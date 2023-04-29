from typing import Any, Awaitable

from aiogram.types import CallbackQuery


class ContinuousCommand:
    def __init__(
        self,
        command: Any,
        finish: Awaitable,
        next: Any,
    ):
        self.command = command

        self._finish = finish
        self._next = next

    async def finish(self, query: CallbackQuery) -> None:
        is_finished = await self._finish(query)
        if (
            is_finished
            and not await self._next.is_finished(query.message)
            and await self._next.is_applicable(query.message)
        ):
            await self._next.execute(query.message)
        else:
            return None
