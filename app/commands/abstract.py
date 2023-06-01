from __future__ import annotations
from typing import Optional

from aiogram import Bot
from aiogram.types import Message

from app.storage import Storage


class AbstractCommand:
    def __init__(self, bot: Bot, next: Optional['AbstractCommand'], storage: Storage):
        self._bot = bot
        self._next = next
        self._storage = storage

    async def execute(self, message: Message) -> None:
        raise NotImplementedError

    async def is_applicable(self, message: Message) -> bool:
        raise NotImplementedError

    async def is_finished(self, message: Message) -> bool:
        raise NotImplementedError

    async def execute_next_if_applicable(self, message: Message) -> None:
        if (
            await self._next.is_applicable(message)
            and not await self._next.is_finished(message)
        ):
            await self._next.execute(message)
        else:
            return None

    async def remove_temporary_messages(self, chat_id: int) -> None:
        message_ids = await self._storage.get_temporary_message_ids(chat_id)
        for message_id in message_ids:
            try:
                await self._bot.delete_message(chat_id, message_id)
            except Exception:
                pass
            await self._storage.remove_temporary_message_id(chat_id, message_id)
