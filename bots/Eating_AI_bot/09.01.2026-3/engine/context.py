from sqlalchemy.orm import Session
from database.models import UserParam, Trace, UserSession, Block
from datetime import datetime
from typing import List, Optional


class ContextHelper:
    def __init__(self, db: Session, user_id: str, platform: str, connector, module_manager):
        self.db = db
        self.user_id = user_id
        self.platform = platform
        self.connector = connector
        self.module_manager = module_manager
        self.should_stop = False  # Flag to stop execution if go_to is called

    # ───────────────────────────────
    # Modules
    # ───────────────────────────────

    def module_start(self, name: str):
        """Force initialization of a module."""
        self.module_manager.load_module(name)

    def call_module(self, name: str, func_name: str, *args):
        """Call a function in a module."""
        module = self.module_manager.get_module(name)
        if not hasattr(module, func_name):
            raise AttributeError(f"Module {name} has no function {func_name}")
        return getattr(module, func_name)(*args)

    # ───────────────────────────────
    # Params
    # ───────────────────────────────

    def set_param(self, key: str, value: str):
        param = self.db.query(UserParam).filter_by(
            user_id=self.user_id,
            platform=self.platform,
            key=key
        ).first()

        if param:
            param.value = str(value)
        else:
            param = UserParam(
                user_id=self.user_id,
                platform=self.platform,
                key=key,
                value=str(value)
            )
            self.db.add(param)

        self.db.commit()

    def get_param(self, key: str):
        param = self.db.query(UserParam).filter_by(
            user_id=self.user_id,
            platform=self.platform,
            key=key
        ).first()
        return param.value if param else None

    # ───────────────────────────────
    # Messaging
    # ───────────────────────────────

    async def send_message(
        self,
        text: str,
        buttons: Optional[List[str]] = None,
        parse_mode: str = "text",
        request_contact: bool = False
    ):
        """
        Unified send_message compatible with BotProvider

        :param text: message text
        :param buttons: reply buttons
        :param parse_mode: text | markdown | html
        :param request_contact: request phone number
        """

        if not text:
            return

        MAX_LENGTH = 4000
        parts = []

        # Split long messages safely
        if len(text) <= MAX_LENGTH:
            parts.append(text)
        else:
            remaining = text
            while remaining:
                if len(remaining) <= MAX_LENGTH:
                    parts.append(remaining)
                    break

                split_index = remaining.rfind('\n', 0, MAX_LENGTH)
                if split_index == -1:
                    split_index = remaining.rfind(' ', 0, MAX_LENGTH)
                if split_index == -1:
                    split_index = MAX_LENGTH

                parts.append(remaining[:split_index])
                remaining = remaining[split_index:].lstrip()

        for i, part in enumerate(parts):
            # ── Trace log
            trace = Trace(
                user_id=self.user_id,
                platform=self.platform,
                direction='outbound',
                content=part,
                created_at=datetime.utcnow()
            )

            session = self.db.query(UserSession).filter_by(
                user_id=self.user_id,
                platform=self.platform
            ).first()

            if session:
                trace.block_id = session.current_block_id

            self.db.add(trace)
            self.db.commit()

            # Buttons only on last message part
            current_buttons = buttons if i == len(parts) - 1 else None
            current_request_contact = request_contact if i == len(parts) - 1 else False

            await self.connector.send_message(
                user_id=self.user_id,
                text=part,
                buttons=current_buttons,
                parse_mode=parse_mode,
                request_contact=current_request_contact
            )

    # ───────────────────────────────
    # Navigation
    # ───────────────────────────────

    def go_to(self, block_id: int):
        session = self.db.query(UserSession).filter_by(
            user_id=self.user_id,
            platform=self.platform
        ).first()

        if session:
            session.current_block_id = block_id
            session.updated_at = datetime.utcnow()
            self.db.commit()
            self.should_stop = True
