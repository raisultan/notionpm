from typing import Any, Final

from aiogram import Bot
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.callback_data import CallbackData

from app.commands.abstract import AbstractCommand
from app.storage import Storage
from app.notion import NotionClient

ChooseDatabaseCallback: Final[CallbackData] = CallbackData("choose_db", "db_id", "db_title")


class ChooseDatabaseCommand(AbstractCommand):
    """Command to choose a database to track."""

    def __init__(
        self,
        bot: Bot,
        next: AbstractCommand,
        storage: Storage,
        notion: NotionClient,
    ):
        super().__init__(bot, next)
        self._storage = storage
        self._notion = notion

    async def is_applicable(self, message: Message) -> bool:
        access_token = await self._storage.get_user_access_token(message.from_user.id)
        print(f'GOT AT FOR USER {message.from_user.id} ACCESS TOKEN {access_token}')
        return bool(access_token)

    async def is_finished(self, message: Message) -> bool:
        return bool(await self._storage.get_user_db_id(message.from_user.id))

    async def execute(self, message: Message) -> None:
        chat_id = message.chat.id
        access_token = await self._storage.get_user_access_token(message.from_user.id)
        print(f'GOT AT FOR USER {message.from_user.id} ACCESS TOKEN {access_token}')
        user_notion = self._notion(auth=access_token)
        databases = user_notion.list_databases()

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
            await self._storage.set_user_db_id(message.from_user.id, db.id)
            print(f'SET DB FOR USER {message.from_user.id} DB ID {db.id}')
            await self._bot.send_message(
                message.chat.id,
                f"Yeah, default database has been set to {db.title} 🎉",
            )
            return None

        inline_keyboard = []

        for db in databases:
            button = InlineKeyboardButton(
                db.title,
                callback_data=ChooseDatabaseCallback.new(db_id=db.id, db_title=db.title),
            )
            inline_keyboard.append([button])

        markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        current_db_id = await self._storage.get_user_db_id(message.from_user.id)
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

        await self._storage.set_user_db_id(query.message.from_user.id, db_id)
        print(f'SET DB FOR USER {query.message.from_user.id} DB ID {db_id}')
        await self._bot.send_message(
            chat_id,
            f"Default database has been set to {data.get('db_title')} 🎉",
        )
        await self.execute_next_if_applicable(query)
