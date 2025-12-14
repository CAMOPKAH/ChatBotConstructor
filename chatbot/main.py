import asyncio
import os
from dotenv import load_dotenv
from database.base import Base, engine, SessionLocal
from connectors.telegram import TelegramBotProvider
from engine.core import ChatbotEngine

# Load env
load_dotenv()

async def main():
    # 1. Init DB
    print("Initializing database...")
    Base.metadata.create_all(bind=engine)

    # 2. Init Connector
    token = os.getenv("TG_TOKEN")
    if not token:
        print("Error: TG_TOKEN not found in .env")
        return

    connector = TelegramBotProvider(token)

    # 3. Init Engine
    chatbot_engine = ChatbotEngine(SessionLocal, connector)

    # 4. Link Connector -> Engine
    connector.set_callback(chatbot_engine.process_message)

    # 5. Start Polling
    print("Starting bot...")
    await connector.listen()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
