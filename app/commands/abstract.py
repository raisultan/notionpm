from __future__ import annotations
from typing import Optional

from aiogram import Bot
from aiogram.types import CallbackQuery, Message


class AbstractCommand:
    def __init__(self, bot: Bot, next: Optional['AbstractCommand']):
        self._bot = bot
        self._next = next

    async def execute(self, message: Message) -> None:
        raise NotImplementedError

    async def is_applicable(self, message: Message) -> bool:
        raise NotImplementedError

    async def is_finished(self, message: Message) -> bool:
        raise NotImplementedError

    async def execute_next_if_applicable(self, query: CallbackQuery) -> None:
        print(f'\n\n{self} APPLICABLE: {await self._next.is_applicable(query.message)}, FINISHED: {not bool(await self._next.is_finished(query.message))}\n\n')
        if (
            await self._next.is_applicable(query.message)
            and not await self._next.is_finished(query.message)
        ):
            await self._next.execute(query.message)
        else:
            return None
