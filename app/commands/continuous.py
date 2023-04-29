from typing import Any, Awaitable


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

    async def finish(self, *args, **kwargs) -> None:
        is_finished = await self._finish(*args, **kwargs)
        if (
            is_finished
            and not await self._next.is_finished()
            and await self._next.is_applicable()
        ):
            await self._next.execute(*args, **kwargs)
        else:
            return None
