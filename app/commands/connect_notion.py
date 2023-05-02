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
        super().__init__(bot, next)
        self._storage = storage
        self._notion_oauth = notion_oauth
        self._next = next

    async def is_applicable(self, message: Message) -> bool:
        return not await self.is_finished(message)

    async def is_finished(self, message: Message) -> bool:
        return bool(await self._storage.get_user_access_token(message.chat.id))

    async def execute(self, message: Message) -> None:
        connect_url = self._notion_oauth.generate_connect_url(message.chat.id)
        button = InlineKeyboardButton(text="Connect Notion📖", url=connect_url)
        markup = InlineKeyboardMarkup(inline_keyboard=[[button]])
        reply = f"Connect your Notion workspace"

        await self._storage.set_user_private_chat_id(message.from_user.id, message.chat.id)
        connect_message = await self._bot.send_message(
            message.chat.id,
            reply,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
        )
        await self._storage.set_connect_message_id(message.chat.id, connect_message.message_id)

    async def handle_oauth(self, request: Request):
        user_id = await self._notion_oauth.handle_oauth(request)
        if user_id:
            chat_id = await self._storage.get_user_private_chat_id(user_id)
            chat = Chat(id=chat_id, type='private')
            user = User(id=user_id, is_bot=False, first_name='dummy', username='dummy')

            message_data = {
                'chat': chat.to_python(),
                'from': user.to_python(),
                'message_id': 0,
            }

            query = CallbackQuery(
                id='dummy_id',
                from_user=user,
                chat_instance=None,
                message=Message(**message_data),
                data="no_callback_data",
            )
            await self.execute_next_if_applicable(query)
            return web.HTTPFound(BOT_URL)
        else:
            return web.Response(status=400)
