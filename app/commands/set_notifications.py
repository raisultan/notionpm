from typing import Final

from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from aiogram.utils.callback_data import CallbackData

from app.commands.abstract import AbstractCommand

SetupNotificationsCallback: Final[CallbackData] = CallbackData("set_notification", "notification_type")


class SetupNotificationsCommand(AbstractCommand):
    async def is_applicable(self, message: Message) -> bool:
        tracked_properties = await self._storage.get_user_tracked_properties(message.chat.id)
        return bool(tracked_properties)

    async def is_finished(self, message: Message) -> bool:
        notification_chat_id = await self._storage.get_user_notification_chat_id(message.chat.id)
        return bool(notification_chat_id)

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

        sent_message = await self._bot.send_message(
            chat_id,
            "Choose where you would like to receive notifications:",
            reply_markup=markup,
        )
        await self._storage.add_temporaty_message_id(chat_id, sent_message.message_id)

    async def handle_private_messages(self, query: CallbackQuery) -> None:
        chat_id = query.message.chat.id
        data = SetupNotificationsCallback.parse(query.data)
        notification_type = data.get("notification_type")

        if notification_type == "private":
            await self._storage.set_user_notification_chat_id(chat_id, chat_id)
            await self._storage.set_user_notification_is_active(chat_id, True)
            await self.remove_temporary_messages(chat_id)
            keyboard = await self._next.get_notifications_keyboard(chat_id)
            await self._bot.send_message(
                    chat_id,
                    "Congratulations! 🎉 Your setup process is complete. "
                    "You can now start tracking changes in your Notion workspace.",
                    reply_markup=keyboard
                )
        else:
            sent_message = await self._bot.send_message(chat_id, "Something went wrong, please try again 🥺")
            await self._storage.add_temporaty_message_id(chat_id, sent_message.message_id)
            await self.execute(query.message)

    async def handle_group_chat(self, message: Message) -> None:
        chat_id = message.chat.id
        from_user_id = message.from_user.id
        bot_user = await self._bot.me

        if message.new_chat_members[0].is_bot and message.new_chat_members[0].id == bot_user.id:
            private_chat_id = await self._storage.get_user_private_chat_id(from_user_id)
            await self._storage.set_user_notification_chat_id(private_chat_id, chat_id)
            await self._storage.set_user_notification_is_active(private_chat_id, True)

            await self._bot.send_message(
                    chat_id,
                    "Heey guys! I'm here to help you track changes in your Notion workspace 🤖",
                )
            await self.remove_temporary_messages(private_chat_id)
            keyboard = await self._next.get_notifications_keyboard(private_chat_id)
            await self._bot.send_message(
                    private_chat_id,
                    "Congratulations! 🎉 Your setup process is complete. "
                    "You can now start tracking changes in your Notion workspace.",
                    reply_markup=keyboard,
                )
        else:
            return None
