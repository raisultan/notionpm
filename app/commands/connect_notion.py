from aiogram import types
from aiogram.types import ParseMode
from aiohttp import web
from aiohttp.web_request import Request

import app.storage as storage
from app.initializer import BOT_URL, bot, notion_oauth
from app.commands.common import skip_or_continue_setup


async def send_login_url(message: types.Message):
    connect_url = notion_oauth.generate_connect_url(message.chat.id)
    button = types.InlineKeyboardButton(text="Connect Notion📖", url=connect_url)
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[button]])
    reply = f"Connect your Notion workspace"

    connect_message = await bot.send_message(
        message.chat.id,
        reply,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
    )
    await storage.set_connect_message_id(message.chat.id, connect_message.message_id)


async def handle_oauth(request: Request):
    chat_id = await notion_oauth.handle_oauth(request)
    if chat_id:
        message = types.Message(chat=types.Chat(id=int(chat_id), type='private'))
        await skip_or_continue_setup(message)
        return web.HTTPFound(BOT_URL)
    else:
        return web.Response(status=400)
