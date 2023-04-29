from aiogram import types
from aiogram.types import CallbackQuery
from aiogram.utils.callback_data import CallbackData

import app.storage as storage
from app.initializer import bot


set_notification_callback_data = CallbackData("set_notification", "notification_type")
async def set_notification_handler(message: types.Message):
    chat_id = message.chat.id
    bot_username = (await bot.me).username
    add_to_group_url = f"https://t.me/{bot_username}?startgroup=0"

    private_button = types.InlineKeyboardButton(
        "Stay here 👨‍💻",
        callback_data=set_notification_callback_data.new(notification_type="private")
    )
    group_button = types.InlineKeyboardButton(
        "Track in group chat 👥",
        url=add_to_group_url,
    )
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[private_button, group_button]])

    await bot.send_message(
        chat_id,
        "Choose where you would like to receive notifications:",
        reply_markup=markup,
    )


async def set_notification_callback_handler(callback_query: CallbackQuery, callback_data: dict):
    chat_id = callback_query.message.chat.id
    notification_type = callback_data.get("notification_type")

    if notification_type == "private":
        await storage.set_user_notification_type(chat_id, "private")
        await storage.set_user_notification_chat_id(callback_query.from_user.id, chat_id)
        await bot.send_message(
            chat_id,
            "Roger that! I will send you notifications in this chat 🤖",
        )
        await bot.send_message(
                chat_id,
                "Congratulations! 🎉 Your setup process is complete. "
                "You can now start tracking changes in your Notion workspace.",
            )
        await storage.set_user_setup_status(chat_id, False)
    else:
        await bot.send_message(chat_id, "Something went wrong, please try again 🥺")
        await set_notification_handler(callback_query.message)

async def on_chat_member_updated(message: types.Message):
    chat_id = message.chat.id
    from_user_id = message.from_user.id
    bot_user = await bot.me

    if message.new_chat_members[0].is_bot and message.new_chat_members[0].id == bot_user.id:
        await storage.set_user_notification_type(from_user_id, "group")
        await storage.set_user_notification_chat_id(from_user_id, chat_id)

        user_private_chat_id = await storage.get_user_private_chat_id(from_user_id)
        await bot.send_message(
                chat_id,
                "Heey guys! I'm here to help you track changes in your Notion workspace 🤖",
            )
        await bot.send_message(
                user_private_chat_id,
                "Congratulations! 🎉 Your setup process is complete. "
                "You can now start tracking changes in your Notion workspace.",
            )
        await storage.set_user_setup_status(from_user_id, False)
    else:
        return
