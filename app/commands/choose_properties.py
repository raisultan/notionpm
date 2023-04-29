from aiogram import types
from aiogram.utils import exceptions
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.callback_data import CallbackData
from notion_client import Client as NotionCLI

import app.storage as storage

from app.initializer import bot
from app.commands.set_notifications import set_notification_handler

SUPPORTED_PROPERTY_TYPES = [
    'title',
    'status',
    'date',
    'people',
    'url',
]


choose_property_callback_data = CallbackData("choose_property", "prop_name")
async def choose_properties_handler(message: types.Message):
    chat_id = message.chat.id
    access_token = await storage.get_user_access_token(chat_id)

    sent_message_id = await storage.get_tracked_properties_message_id(chat_id)
    if sent_message_id:
        await bot.delete_message(chat_id, sent_message_id)
        await storage.delete_tracked_properties_message_id(chat_id)

    # TODO: repeated code
    if not access_token:
        await bot.send_message(
            chat_id,
            "You need to connect your Notion workspace first. Use the /login command to connect.",
        )
        return

    # TODO: repeated code
    db_id = await storage.get_user_db_id(chat_id)
    if not db_id:
        await bot.send_message(
            chat_id,
            "You must choose a default database first. Use the /choose_database command.",
        )
        return

    user_notion = NotionCLI(auth=access_token)
    database = user_notion.databases.retrieve(db_id)
    supported_properties = {
        prop_name: prop
        for prop_name, prop in database['properties'].items()
        if prop['type'] in SUPPORTED_PROPERTY_TYPES
    }
    property_buttons = []

    for prop_name, _ in supported_properties.items():
        button = InlineKeyboardButton(
            prop_name,
            callback_data=choose_property_callback_data.new(prop_name=prop_name),
        )
        property_buttons.append([button])

    markup = InlineKeyboardMarkup(inline_keyboard=property_buttons)

    done_button = KeyboardButton("Done selecting✅")
    done_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    done_markup.add(done_button)

    await bot.send_message(
        chat_id,
        "Choose the properties you want to track:",
        reply_markup=markup,
    )

    await bot.send_message(
        chat_id,
        "Press 'Done selecting✅' when you're finished selecting properties🤖",
        reply_markup=done_markup,
    )


async def choose_property_callback_handler(callback_query: CallbackQuery, callback_data: dict):
    chat_id = callback_query.message.chat.id
    prop_name = callback_data.get("prop_name")
    tracked_properties = await storage.get_user_tracked_properties(chat_id)

    if not tracked_properties:
        tracked_properties = []

    if prop_name not in tracked_properties:
        tracked_properties.append(prop_name)
    else:
        tracked_properties.remove(prop_name)

    await storage.set_user_tracked_properties(chat_id, tracked_properties)

    if tracked_properties:
        new_text = f"Current tracked properties: {', '.join(tracked_properties)}"
    else:
        new_text = "No properties have been selected."

    message_id = await storage.get_tracked_properties_message_id(chat_id)
    if not message_id:
        sent_message = await bot.send_message(
            chat_id,
            text=new_text,
        )
        await storage.set_tracked_properties_message_id(chat_id, sent_message.message_id)
    else:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=new_text,
            )
        except exceptions.MessageNotModified:
            pass


async def properties_done_handler(message: types.Message):
    chat_id = message.chat.id
    tracked_properties = await storage.get_user_tracked_properties(chat_id)
    from_user_id = message.from_user.id

    sent_message_id = await storage.get_tracked_properties_message_id(chat_id)
    if sent_message_id:
        await bot.delete_message(chat_id, sent_message_id)
        await storage.delete_tracked_properties_message_id(chat_id)

    if not tracked_properties:
        await bot.send_message(
            chat_id,
            "No properties have been selected. Please choose at least one property.",
        )
        await choose_properties_handler(message)
    else:
        await bot.send_message(
            chat_id,
            f"Selected properties: {', '.join(tracked_properties)}",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        is_in_setup = await storage.get_user_setup_status(chat_id)
        if is_in_setup:
            await storage.set_user_private_chat_id(from_user_id, chat_id)
            await set_notification_handler(message)
