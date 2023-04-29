from aiogram.types import Message

from app.commands.common import skip_or_continue_setup


class StartCommand:
    async def is_applicable(self) -> bool:
        return True

    async def is_finished(self, message: Message) -> bool:
        return True

    async def execute(self, message: Message) -> None:
        if message.chat.type != "private":
            return
        await skip_or_continue_setup(message)
