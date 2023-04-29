from aiogram import types

from app.commands.common import skip_or_continue_setup


async def send_welcome(message: types.Message):
    if message.chat.type != "private":
        return
    await skip_or_continue_setup(message)
