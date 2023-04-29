from aiogram.types import Message

from app.commands.common import skip_or_continue_setup


class StartCommand:
    async def execute(self, message: Message) -> None:
        if message.chat.type != "private":
            return
        await skip_or_continue_setup(message)
