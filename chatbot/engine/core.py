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

    async def process_message(self, user_id: str, platform: str, text: str):
        db: Session = self.db_session_factory()
        try:
            # 0. Check User Status
            user = db.query(BotUser).filter_by(user_id=user_id, platform=platform).first()
            if not user:
                # Auto-create new user
                user = BotUser(user_id=user_id, platform=platform, is_active=True)
                db.add(user)
                db.commit()
            
            if not user.is_active:
                print(f"Ignored message from inactive user {user_id}")
                return

            # 1. Log Inbound
            session = db.query(UserSession).filter_by(user_id=user_id, platform=platform).first()
            current_block_id = session.current_block_id if session else None

            trace = Trace(
                user_id=user_id,
                platform=platform,
                block_id=current_block_id,
                direction='inbound',
                content=text,
                created_at=datetime.utcnow()
            )
            db.add(trace)
            db.commit()

            # 2. Session Management
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
                current_block_id = start_block.id
            
            # 3. Load Block
            event = 'message'
            
            while True:
                block = db.query(Block).filter_by(id=session.current_block_id).first()
                if not block:
                    print(f"Error: Block {session.current_block_id} not found")
                    break

                # 4. Context
                helper = ContextHelper(db, user_id, platform, self.connector, self.module_manager)
                
                context = {
                    'input_text': text,
                    'event': event,
                    'set_param': helper.set_param,
                    'get_param': helper.get_param,
                    'send_message': helper.send_message,
                    'go_to': helper.go_to,
                    'ModuleStart': helper.module_start,
                    'call_module': helper.call_module,
                    'print': print # Debugging
                }

                # 5. Execution
                try:
                    # Redefine context for sync execution
                    outbox = []
                    def sync_send_message(msg_text, buttons=None):
                        outbox.append((msg_text, buttons))
                    
                    context['send_message'] = sync_send_message
                    
                    # Run the script
                    exec(block.script_code, context)
                    
                    # Process outbox
                    for msg_text, buttons in outbox:
                        await helper.send_message(msg_text, buttons)
                    
                    # Check for transition
                    if helper.should_stop:
                        event = 'enter'
                        continue 
                    else:
                        break
                except Exception as e:
                    print(f"Error executing block {block.id}: {e}")
                    traceback.print_exc()
                    await self.connector.send_message(user_id, "Произошла ошибка в работе бота.")
                    break

        finally:
            db.close()
