from aiogram import types
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.callback_data import CallbackData
from notion_client import Client as NotionCLI

import app.storage as storage
from app.notion import list_databases

from app.commands.common import skip_or_continue_setup
from app.initializer import bot


choose_db_callback_data = CallbackData("choose_db", "db_id", "db_title")
async def choose_database_handler(message: types.Message):
    chat_id = message.chat.id
    access_token = await storage.get_user_access_token(chat_id)

    # TODO: repeated code
    if not access_token:
        await bot.send_message(
            chat_id,
            "You need to connect your Notion workspace first. Use the /login command to connect.",
        )
        return

    user_notion = NotionCLI(auth=access_token)
    databases = list_databases(user_notion)

    # TODO: repeated code
    if not databases:
        await bot.send_message(message.chat.id, "No databases found in your Notion workspace.")
        return

    connect_message_id = await storage.get_connect_message_id(message.chat.id)
    if connect_message_id:
        await bot.delete_message(chat_id, connect_message_id)

    if len(databases) == 1:
        db = databases[0]
        await storage.set_user_db_id(message.chat.id, db.id)
        await bot.send_message(
            message.chat.id,
            f"Yeah, default database has been set to {db.title} 🎉",
        )
        await skip_or_continue_setup(message)
        return

    inline_keyboard = []

    for db in databases:
        button = InlineKeyboardButton(
            db.title,
            callback_data=choose_db_callback_data.new(db_id=db.id, db_title=db.title),
        )
        inline_keyboard.append([button])

    markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    current_db_id = await storage.get_user_db_id(message.chat.id)
    if current_db_id:
        text = (
            "You have already chosen a default database. "
            "You can choose a new one from the list below:"
        )
        await bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        await bot.send_message(
            message.chat.id,
            "Choose the default database for team tasks:",
            reply_markup=markup,
        )


async def choose_db_callback_handler(callback_query: CallbackQuery, callback_data: dict):
    db_id = callback_data.get("db_id")
    chat_id = callback_query.message.chat.id

    await storage.set_user_db_id(chat_id, db_id)
    await bot.send_message(
        chat_id,
        f"Default database has been set to {callback_data.get('db_title')} 🎉",
    )
    await skip_or_continue_setup(callback_query.message)
