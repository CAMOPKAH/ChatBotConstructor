import traceback
from sqlalchemy.orm import Session
from database.models import UserSession, Block, Trace, BotUser
from .context import ContextHelper
from .manager import ModuleManager
from datetime import datetime


class ChatbotEngine:
    def __init__(self, db_session_factory, connector):
        self.db_session_factory = db_session_factory
        self.connector = connector
        self.module_manager = ModuleManager(db_session_factory)

    async def process_message(
        self,
        user_id: str,
        platform: str,
        text: str,
        user_data: dict = None
    ):
        db: Session = self.db_session_factory()

        try:
            # ───────────────────────────────
            # 0. User management
            # ───────────────────────────────

            user = db.query(BotUser).filter_by(
                user_id=user_id,
                platform=platform
            ).first()

            username = user_data.get("username") if user_data else None

            if not user:
                user = BotUser(
                    user_id=user_id,
                    platform=platform,
                    username=username,
                    is_active=True
                )
                db.add(user)
                db.commit()
            else:
                if username and user.username != username:
                    user.username = username
                    db.commit()

            # Save user_data → UserParam
            if user_data:
                from database.models import UserParam
                for key, value in user_data.items():
                    if key == "username" or value is None:
                        continue

                    param = db.query(UserParam).filter_by(
                        user_id=user_id,
                        platform=platform,
                        key=key
                    ).first()

                    if param:
                        param.value = str(value)
                    else:
                        db.add(UserParam(
                            user_id=user_id,
                            platform=platform,
                            key=key,
                            value=str(value)
                        ))
                db.commit()

            if not user.is_active:
                print(f"Ignored message from inactive user {user_id}")
                return

            # ───────────────────────────────
            # 1. Log inbound
            # ───────────────────────────────

            session = db.query(UserSession).filter_by(
                user_id=user_id,
                platform=platform
            ).first()

            trace = Trace(
                user_id=user_id,
                platform=platform,
                block_id=session.current_block_id if session else None,
                direction="inbound",
                content=text,
                created_at=datetime.utcnow()
            )
            db.add(trace)
            db.commit()

            # ───────────────────────────────
            # 2. Session initialization
            # ───────────────────────────────

            if not session:
                start_block = db.query(Block).filter_by(is_start=True).first()
                if not start_block:
                    print("Error: No start block found!")
                    return

                session = UserSession(
                    user_id=user_id,
                    platform=platform,
                    current_block_id=start_block.id
                )
                db.add(session)
                db.commit()

            # ───────────────────────────────
            # 3. Block execution loop
            # ───────────────────────────────

            event = "message"

            while True:
                block = db.query(Block).filter_by(
                    id=session.current_block_id
                ).first()

                if not block:
                    print(f"Error: Block {session.current_block_id} not found")
                    break

                helper = ContextHelper(
                    db=db,
                    user_id=user_id,
                    platform=platform,
                    connector=self.connector,
                    module_manager=self.module_manager
                )

                # ───────────────────────────────
                # 4. Execution context
                # ───────────────────────────────

                outbox = []

                def sync_send_message(
                    text,
                    buttons=None,
                    parse_mode="text",
                    request_contact=False
                ):
                    """
                    Backward-compatible wrapper:
                    send_message(text)
                    send_message(text, buttons)
                    send_message(text, buttons, parse_mode, request_contact)
                    """
                    outbox.append({
                        "text": text,
                        "buttons": buttons,
                        "parse_mode": parse_mode,
                        "request_contact": request_contact
                    })

                context = {
                    "input_text": text,
                    "event": event,
                    "set_param": helper.set_param,
                    "get_param": helper.get_param,
                    "send_message": sync_send_message,
                    "go_to": helper.go_to,
                    "ModuleStart": helper.module_start,
                    "call_module": helper.call_module,
                    "print": print
                }

                # ───────────────────────────────
                # 5. Execute block
                # ───────────────────────────────

                try:
                    exec(block.script_code, context)

                    # Flush outbox
                    for msg in outbox:
                        await helper.send_message(
                            text=msg["text"],
                            buttons=msg["buttons"],
                            parse_mode=msg["parse_mode"],
                            request_contact=msg["request_contact"]
                        )

                    if helper.should_stop:
                        event = "enter"
                        continue
                    else:
                        break

                except Exception as e:
                    print(f"Error executing block {block.id}: {e}")
                    traceback.print_exc()
                    await self.connector.send_message(
                        user_id,
                        "⚠️ Произошла ошибка в работе бота"
                    )
                    break

        finally:
            db.close()
