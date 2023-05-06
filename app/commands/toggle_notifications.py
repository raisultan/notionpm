from aiogram import Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from app.commands.abstract import AbstractCommand
from app.storage import Storage


class ToggleNotificationsCommand(AbstractCommand):
    def __init__(self, bot: Bot, storage: Storage):
        super().__init__(bot, None, storage)

    async def is_applicable(self, message: Message) -> bool:
        return True

    async def is_finished(self, message: Message) -> bool:
        return False

    async def get_notifications_keyboard(self, chat_id: int) -> ReplyKeyboardMarkup:
        is_notifications_active = await self._storage.get_user_notification_is_active(chat_id)
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        if is_notifications_active:
            button = KeyboardButton("Pause notifications ⏸️")
        else:
            button = KeyboardButton("Unpause notifications ⏯️")

        keyboard.add(button)
        return keyboard

    async def execute(self, message: Message) -> None:
        chat_id = message.chat.id
        is_notifications_active = await self._storage.get_user_notification_is_active(chat_id)
        if is_notifications_active:
            await self._storage.set_user_notification_is_active(chat_id, False)
            message = "Notifications are paused. You can unpause them anytime 🥷"
        else:
            await self._storage.set_user_notification_is_active(chat_id, True)
            message = "Notifications are unpaused. You can pause them anytime 🦖"

        keyboard = await self.get_notifications_keyboard(chat_id)
        await self._bot.send_message(
            chat_id,
            message,
            reply_markup=keyboard,
        )
