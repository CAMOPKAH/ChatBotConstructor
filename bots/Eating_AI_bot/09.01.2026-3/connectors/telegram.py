import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)
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

            user_data = {
                "username": message.from_user.username,
                "first_name": message.from_user.first_name,
                "last_name": message.from_user.last_name,
                "language_code": message.from_user.language_code,
                "is_premium": getattr(message.from_user, "is_premium", False),
                "contact": message.contact.phone_number if message.contact else None
            }

            await self.on_message(user_id, 'telegram', text, user_data)

    async def listen(self):
        print("Telegram Bot started polling...")
        await self.dp.start_polling(self.bot)

    async def send_message(
        self,
        user_id: str,
        text: str,
        buttons: list[str] = None,
        parse_mode: str = "text",
        request_contact: bool = False
    ):
        """
        parse_mode: text | markdown | html
        request_contact: True -> adds button to share phone number
        """


        
        try:
            markup = None

            if buttons or request_contact:
                keyboard = []

                # Обычные кнопки (обратная совместимость)
                if buttons:
                    for btn in buttons:
                        keyboard.append([KeyboardButton(text=btn)])

                # Кнопка запроса номера телефона
                if request_contact:
                    
                    keyboard.append([
                        KeyboardButton(
                            text=text,
                            request_contact=True
                        )
                    ])

                markup = ReplyKeyboardMarkup(
                    keyboard=keyboard,
                    resize_keyboard=True,
                    one_time_keyboard=True
                )

            # Приводим parse_mode к aiogram-совместимому
            tg_parse_mode = None
            if parse_mode == "markdown":
                tg_parse_mode = "MarkdownV2"
            elif parse_mode == "html":
                tg_parse_mode = "HTML"

            await self.bot.send_message(
                chat_id=user_id,
                text=text,
                reply_markup=markup,
                parse_mode=tg_parse_mode
            )

        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")
        
        #keyboard = ReplyKeyboardMarkup(
        #keyboard=[
        #[KeyboardButton(text=text, request_contact=True)]
        #],
        #resize_keyboard=True,
        #one_time_keyboard=True
        #)
        #await self.bot.send_message(
        #chat_id=user_id,
        #text="📞 *Номер телефона*\nНажмите кнопку ниже",
        #reply_markup=keyboard,
        #parse_mode="MarkdownV2")