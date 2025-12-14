from abc import ABC, abstractmethod

class BotProvider(ABC):
    def __init__(self):
        self.on_message = None # Callback function(user_id, platform, text)

    def set_callback(self, callback):
        self.on_message = callback

    @abstractmethod
    async def listen(self):
        pass

    @abstractmethod
    async def send_message(self, user_id: str, text: str, buttons: list[str] = None):
        pass
