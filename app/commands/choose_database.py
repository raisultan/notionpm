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
        super().__init__(bot, next, storage)
        self._notion = notion

    async def is_applicable(self, message: Message) -> bool:
        access_token = await self._storage.get_user_access_token(message.chat.id)
        return bool(access_token)

    async def is_finished(self, message: Message) -> bool:
        return bool(await self._storage.get_user_db_id(message.chat.id))

    async def execute(self, message: Message) -> None:
        chat_id = message.chat.id
        access_token = await self._storage.get_user_access_token(chat_id)
        user_notion = self._notion(auth=access_token)
        databases = user_notion.list_databases()

        if not databases:
            await self._bot.send_message(
                chat_id,
                "No databases found in your Notion workspace, please choose valid database 📄",
            )
            await self.execute(message)
            return None

        await self.remove_temporary_messages(chat_id)
        if len(databases) == 1:
            db = databases[0]
            db_id = db.id
            await self._storage.set_user_db_id(chat_id, db.id)
            await self._bot.send_message(
                chat_id,
                f"Hooray! Default database has been set to {db.title} 🎉",
            )

            access_token = await self._storage.get_user_access_token(chat_id)
            db_state = user_notion.databases.query(database_id=db_id)
            await self._storage.set_user_db_state(db_id, db_state)

            await self.execute_next_if_applicable(message)
            return None

        inline_keyboard = []

        for db in databases:
            escaped_title = db.title.replace(":", "-")
            print('escaped_title', escaped_title)
            button = InlineKeyboardButton(
                db.title,
                callback_data=ChooseDatabaseCallback.new(db_id=db.id, db_title=escaped_title),
            )
            inline_keyboard.append([button])

        markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
        current_db_id = await self._storage.get_user_db_id(chat_id)
        if current_db_id:
            current_db_title = '🤷‍♀️'
            for db in databases:
                if db.id == current_db_id:
                    current_db_title = db.title
            text = (
                f"You have already chosen a default database: {current_db_title}.\n"
                "You can choose a another one from the list below:"
            )
            sent_message = await self._bot.send_message(chat_id, text, reply_markup=markup)
        else:
            sent_message = await self._bot.send_message(
                chat_id,
                "Choose the default database for team tasks:",
                reply_markup=markup,
            )
        await self._storage.add_temporaty_message_id(chat_id, sent_message.message_id)

    async def handle_callback(self, query: CallbackQuery) -> None:
        chat_id = query.message.chat.id
        data = ChooseDatabaseCallback.parse(query.data)
        db_id = data.get("db_id")

        await self._storage.set_user_db_id(query.message.chat.id, db_id)
        await self._bot.send_message(
            chat_id,
            f"Default database has been set to {data.get('db_title')} 🎉",
        )
        await self.remove_temporary_messages(chat_id)

        await self._storage.remove_user_tracked_properties(chat_id)
        access_token = await self._storage.get_user_access_token(chat_id)
        user_notion = self._notion(auth=access_token)
        db_state = user_notion.databases.query(database_id=db_id)
        await self._storage.set_user_db_state(db_id, db_state)
        await self.execute_next_if_applicable(query.message)
