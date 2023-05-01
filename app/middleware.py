from typing import Iterable

from aiogram import Bot
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.handler import CancelHandler
from aiogram.types import Message

from app.commands.abstract import AbstractCommand


class ForceUserSetupMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot, setup_commands: Iterable[AbstractCommand]):
        super().__init__()
        self._bot = bot
        self._setup_commands = setup_commands

    async def on_pre_process_message(self, message: Message, data: dict) -> None:
        for command in self._setup_commands:
            if (
                not await command.is_finished(message)
                and await command.is_applicable(message)
            ):
                await self._bot.send_message(
                    message.chat.id,
                    "Oops, seems like you haven't set me up yet. Let's do that first 😇"
                )
                await command.execute(message)
                raise CancelHandler()
