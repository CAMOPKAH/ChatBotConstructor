from abc import ABC, abstractmethod
from typing import List, Optional


class BotProvider(ABC):
    def __init__(self):
        # Callback: (user_id, platform, text, user_data)
        self.on_message = None

    def set_callback(self, callback):
        self.on_message = callback

    @abstractmethod
    async def listen(self):
        pass

    @abstractmethod
    async def send_message(
        self,
        user_id: str,
        text: str,
        buttons: Optional[List[str]] = None,
        parse_mode: str = "text",
        request_contact: bool = False
    ):
        """
        send_message contract (platform-agnostic)

        :param user_id: platform user id
        :param text: message text
        :param buttons: simple reply buttons (optional)
        :param parse_mode: text | markdown | html
        :param request_contact: ask user to share phone number
        """
        pass
