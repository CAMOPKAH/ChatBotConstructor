import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from .base import BotProvider

class TelegramBotProvider(BotProvider):
    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self.bot = Bot(token=token)
        self.dp = Dispatcher()
        
        # Register handlers
        self.dp.message.register(self.handle_message)

    async def handle_message(self, message: Message):
        if self.on_message:
            user_id = str(message.from_user.id)
            text = message.text or ""
            # We await the engine processing
            await self.on_message(user_id, 'telegram', text)

    async def listen(self):
        print("Telegram Bot started polling...")
        await self.dp.start_polling(self.bot)

    async def send_message(self, user_id: str, text: str, buttons: list[str] = None):
        try:
            markup = None
            if buttons:
                keyboard = [[KeyboardButton(text=btn)] for btn in buttons]
                markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
            
            await self.bot.send_message(chat_id=user_id, text=text, reply_markup=markup)
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")
