from sqlalchemy.orm import Session
from database.models import UserParam, Trace, UserSession, Block
from datetime import datetime

class ContextHelper:
    def __init__(self, db: Session, user_id: str, platform: str, connector, module_manager):
        self.db = db
        self.user_id = user_id
        self.platform = platform
        self.connector = connector
        self.module_manager = module_manager
        self.should_stop = False # Flag to stop execution if go_to is called

    def module_start(self, name: str):
        """Force initialization of a module."""
        self.module_manager.load_module(name)

    def call_module(self, name: str, func_name: str, *args):
        """Call a function in a module."""
        module = self.module_manager.get_module(name)
        if hasattr(module, func_name):
            func = getattr(module, func_name)
            return func(*args)
        else:
            raise AttributeError(f"Module {name} has no function {func_name}")

    def set_param(self, key: str, value: str):
        param = self.db.query(UserParam).filter_by(
            user_id=self.user_id, platform=self.platform, key=key
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
            user_id=self.user_id, platform=self.platform, key=key
        ).first()
        return param.value if param else None

    async def send_message(self, text: str, buttons: list[str] = None):
        MAX_LENGTH = 4000
        parts = []
        
        if not text:
            return

        if len(text) <= MAX_LENGTH:
            parts.append(text)
        else:
            remaining_text = text
            while remaining_text:
                if len(remaining_text) <= MAX_LENGTH:
                    parts.append(remaining_text)
                    break
                
                # Try to split by newline
                split_index = remaining_text.rfind('\n', 0, MAX_LENGTH)
                if split_index == -1:
                    # Try to split by space
                    split_index = remaining_text.rfind(' ', 0, MAX_LENGTH)
                
                if split_index == -1:
                    # Force split
                    split_index = MAX_LENGTH
                
                parts.append(remaining_text[:split_index])
                remaining_text = remaining_text[split_index:].lstrip()

        for i, part in enumerate(parts):
            # Log outbound
            trace = Trace(
                user_id=self.user_id,
                platform=self.platform,
                direction='outbound',
                content=part,
                created_at=datetime.utcnow()
            )
            
            session = self.db.query(UserSession).filter_by(
                user_id=self.user_id, platform=self.platform
            ).first()
            if session:
                trace.block_id = session.current_block_id
            
            self.db.add(trace)
            self.db.commit()

            # Attach buttons only to the last part
            current_buttons = buttons if i == len(parts) - 1 else None
            await self.connector.send_message(self.user_id, part, current_buttons)

    def go_to(self, block_id: int):
        session = self.db.query(UserSession).filter_by(
            user_id=self.user_id, platform=self.platform
        ).first()
        if session:
            session.current_block_id = block_id
            session.updated_at = datetime.utcnow()
            self.db.commit()
            self.should_stop = True # Signal to stop current block execution and switch
