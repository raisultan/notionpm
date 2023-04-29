from aiogram import Bot
from aiogram.types import Message


class StartCommand:
    def __init__(self, bot: Bot):
        self._bot = bot

    async def is_applicable(self) -> bool:
        return True

    async def is_finished(self, message: Message) -> bool:
        return True

    async def execute(self, message: Message) -> None:
        if message.chat.type != "private":
            return
        await self._bot.send_message(
            message.chat.id,
            "Hi there! Good to see you here 😊\n",
        )
