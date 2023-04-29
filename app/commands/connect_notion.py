from typing import Any

from aiogram import Bot
from aiogram.types import (
    ParseMode,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Chat,
)
from aiohttp import web
from aiohttp.web_request import Request

from app.initializer import BOT_URL
from v0_1.notion_oauth import NotionOAuth


class ConnectNotionCommand:
    def __init__(self, bot: Bot, storage: Any, notion_oauth: NotionOAuth, next: Any):
        self._bot = bot
        self._storage = storage
        self._notion_oauth = notion_oauth
        self._next = next

    async def is_applicable(self, message: Message) -> bool:
        return True

    async def is_finished(self, message: Message) -> bool:
        return bool(await self._storage.get_user_access_token(message.chat.id))

    async def execute(self, message: Message) -> None:
        connect_url = self._notion_oauth.generate_connect_url(message.chat.id)
        button = InlineKeyboardButton(text="Connect Notion📖", url=connect_url)
        markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
        reply = f"Connect your Notion workspace"

        connect_message = await self._bot.send_message(
            message.chat.id,
            reply,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
        )
        await self._storage.set_connect_message_id(message.chat.id, connect_message.message_id)

    async def handle_oauth(self, request: Request):
        chat_id = await self._notion_oauth.handle_oauth(request)
        if chat_id:
            message = Message(chat=Chat(id=int(chat_id), type='private'))
            await self._next.execute(message)
            return web.HTTPFound(BOT_URL)
        else:
            return web.Response(status=400)
