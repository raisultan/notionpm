from typing import Any

from aiogram import Bot
from aiogram.types import (
    ParseMode,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Chat,
    CallbackQuery,
    User,
)
from aiohttp import web
from aiohttp.web_request import Request

from app.initializer import BOT_URL
from app.commands.abstract import AbstractCommand
from v0_1.notion_oauth import NotionOAuth
from app.storage import Storage


class ConnectNotionCommand(AbstractCommand):
    def __init__(
        self,
        bot: Bot,
        next: AbstractCommand,
        storage: Storage,
        notion_oauth: NotionOAuth,
    ):
        super().__init__(bot, next, storage)
        self._notion_oauth = notion_oauth

    async def is_applicable(self, message: Message) -> bool:
        return not await self.is_finished(message)

    async def is_finished(self, message: Message) -> bool:
        return bool(await self._storage.get_user_access_token(message.chat.id))

    async def execute(self, message: Message) -> None:
        chat_id = message.chat.id
        connect_url = self._notion_oauth.generate_connect_url(message.chat.id)
        button = InlineKeyboardButton(text="Connect Notion📖", url=connect_url)
        markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
        reply = f"Connect your Notion workspace"

        await self._storage.set_user_private_chat_id(message.from_user.id, chat_id)
        connect_message = await self._bot.send_message(
            chat_id,
            reply,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
        )
        await self._storage.add_temporaty_message_id(chat_id, connect_message.message_id)

    async def handle_oauth(self, request: Request):
        chat_id = await self._notion_oauth.handle_oauth(request)
        if chat_id:
            message = Message(chat=Chat(id=int(chat_id), type='private'))
            await self.execute_next_if_applicable(message)
            return web.HTTPFound(BOT_URL)
        else:
            return web.Response(status=400)
