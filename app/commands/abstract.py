from __future__ import annotations
from typing import Optional

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, Chat, User


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
        if (
            await self._next.is_applicable(query.message)
            and not await self._next.is_finished(query.message)
        ):
            chat = Chat(id=query.message.chat.id, type='private')
            user = User(id=query.from_user.id, is_bot=False, first_name='dummy', username='dummy')
            message_data = {
                'chat': chat.to_python(),
                'from': user.to_python(),
                'message_id': 0,
            }
            await self._next.execute(Message(**message_data))
        else:
            return None
