from typing import Any, Final

from aiogram import Bot
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.callback_data import CallbackData

from app.commands.abstract import AbstractCommand
from app.storage import Storage

SetupNotificationsCallback: Final[CallbackData] = CallbackData("set_notification", "notification_type")


class SetupNotificationsCommand(AbstractCommand):
    def __init__(self, bot: Bot, next: AbstractCommand, storage: Storage):
        super().__init__(bot, next)
        self._storage = storage

    async def is_applicable(self, message: Message) -> bool:
        tracked_properties = await self._storage.get_user_tracked_properties(message.chat.id)
        return bool(tracked_properties)

    async def is_finished(self, message: Message) -> bool:
        user_id = message.from_user.id
        notification_type = await self._storage.get_user_notification_type(user_id)
        chat_id = await self._storage.get_user_notification_chat_id(user_id)
        return notification_type and chat_id

    async def execute(self, message: Message) -> None:
        chat_id = message.chat.id
        bot_username = (await self._bot.me).username
        add_to_group_url = f"https://t.me/{bot_username}?startgroup=0"

        private_button = InlineKeyboardButton(
            "Stay here 👨‍💻",
            callback_data=SetupNotificationsCallback.new(notification_type="private")
        )
        group_button = InlineKeyboardButton(
            "Track in group chat 👥",
            url=add_to_group_url,
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[[private_button, group_button]])

        await self._bot.send_message(
            chat_id,
            "Choose where you would like to receive notifications:",
            reply_markup=markup,
        )

    async def handle_private_messages(self, query: CallbackQuery) -> None:
        chat_id = query.message.chat.id
        data = SetupNotificationsCallback.parse(query.data)
        notification_type = data.get("notification_type")

        if notification_type == "private":
            await self._storage.set_user_notification_type(chat_id, "private")
            await self._storage.set_user_notification_chat_id(query.from_user.id, chat_id)
            await self._bot.send_message(
                chat_id,
                "Roger that! I will send you notifications in this chat 🤖",
            )
            await self._bot.send_message(
                    chat_id,
                    "Congratulations! 🎉 Your setup process is complete. "
                    "You can now start tracking changes in your Notion workspace.",
                )
            await self._storage.set_user_setup_status(chat_id, False)
        else:
            await self._bot.send_message(chat_id, "Something went wrong, please try again 🥺")
            await self.execute(query.message)

    async def handle_group_chat(self, message: Message) -> None:
        chat_id = message.chat.id
        from_user_id = message.from_user.id
        bot_user = await self._bot.me

        if message.new_chat_members[0].is_bot and message.new_chat_members[0].id == bot_user.id:
            await self._storage.set_user_notification_type(from_user_id, "group")
            await self._storage.set_user_notification_chat_id(from_user_id, chat_id)

            user_private_chat_id = await self._storage.get_user_private_chat_id(from_user_id)
            await self._bot.send_message(
                    chat_id,
                    "Heey guys! I'm here to help you track changes in your Notion workspace 🤖",
                )
            await self._bot.send_message(
                    user_private_chat_id,
                    "Congratulations! 🎉 Your setup process is complete. "
                    "You can now start tracking changes in your Notion workspace.",
                )
            await self._storage.set_user_setup_status(from_user_id, False)
        else:
            return None
