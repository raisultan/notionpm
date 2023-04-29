from typing import Any, Final

from aiogram import Bot
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.callback_data import CallbackData
from notion_client import Client as NotionCLI

from app.commands.common import skip_or_continue_setup

ChooseDatabaseCallback: Final[CallbackData] = CallbackData("choose_db", "db_id", "db_title")


class ChooseDatabaseCommand:
    """Command to choose a database to track."""

    def __init__(self, bot: Bot, storage: Any, notion: NotionCLI, notion_cli: Any):
        self._bot = bot
        self._storage = storage
        self._notion = notion
        self._notion_cli = notion_cli

    async def is_applicable(self, message: Message) -> bool:
        access_token = await self._storage.get_user_access_token(message.chat.id)
        return bool(access_token)

    async def is_finished(self, message: Message) -> bool:
        return bool(await self._storage.get_user_db_id(message.chat.id))

    async def execute(self, message: Message) -> None:
        chat_id = message.chat.id
        access_token = await self._storage.get_user_access_token(chat_id)
        user_notion = self._notion(auth=access_token)
        databases = self._notion_cli.list_databases(user_notion)

        if not databases:
            await self._bot.send_message(
                chat_id,
                "No databases found in your Notion workspace, please choose valid database 📄",
            )
            await self.execute(message)
            return None

        connect_message_id = await self._storage.get_connect_message_id(message.chat.id)
        if connect_message_id:
            await self._bot.delete_message(chat_id, connect_message_id)

        if len(databases) == 1:
            db = databases[0]
            await self._storage.set_user_db_id(message.chat.id, db.id)
            await self._bot.send_message(
                message.chat.id,
                f"Yeah, default database has been set to {db.title} 🎉",
            )
            await skip_or_continue_setup(message)
            return

        inline_keyboard = []

        for db in databases:
            button = InlineKeyboardButton(
                db.title,
                callback_data=ChooseDatabaseCallback.new(db_id=db.id, db_title=db.title),
            )
            inline_keyboard.append([button])

        markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        current_db_id = await self._storage.get_user_db_id(message.chat.id)
        if current_db_id:
            text = (
                "You have already chosen a default database. "
                "You can choose a new one from the list below:"
            )
            await self._bot.send_message(message.chat.id, text, reply_markup=markup)
        else:
            await self._bot.send_message(
                message.chat.id,
                "Choose the default database for team tasks:",
                reply_markup=markup,
            )

    async def handle_callback(self, query: CallbackQuery) -> None:
        chat_id = query.message.chat.id
        data = ChooseDatabaseCallback.parse(query.data)
        db_id = data.get("db_id")

        await self._storage.set_user_db_id(chat_id, db_id)
        await self._bot.send_message(
            chat_id,
            f"Default database has been set to {data.get('db_title')} 🎉",
        )
        await skip_or_continue_setup(query.message)
