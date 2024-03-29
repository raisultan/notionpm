from typing import Final, Optional

from aiogram import Bot
from aiogram import types
from aiogram.utils import exceptions
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

ChoosePropertyCallback: Final[CallbackData] = CallbackData("choose_property", "prop_name")
DonePropertySelectingCallback: Final[CallbackData] = CallbackData("done_property_selecting")


class ChoosePropertiesCommand(AbstractCommand):
    SUPPORTED_PROPERTY_TYPES: Final[list[str]] = [
        'title',
        'status',
        'select',
        'date',
        'people',
        'url',
    ]

    def __init__(
        self,
        bot: Bot,
        next: Optional[AbstractCommand],
        storage: Storage,
        notion: NotionClient,
    ):
        super().__init__(bot, next, storage)
        self._notion = notion

    async def is_applicable(self, message: Message) -> bool:
        db_id = await self._storage.get_user_db_id(message.chat.id)
        return bool(db_id)

    async def is_finished(self, message: Message) -> bool:
        return bool(await self._storage.get_user_tracked_properties(message.chat.id))

    async def execute(self, message: Message) -> None:
        chat_id = message.chat.id

        sent_message_id = await self._storage.get_tracked_properties_message_id(chat_id)
        if sent_message_id:
            await self._delete_tracked_properties_message(chat_id, sent_message_id)

        access_token = await self._storage.get_user_access_token(message.chat.id)
        db_id = await self._storage.get_user_db_id(message.chat.id)
        user_notion = self._notion(auth=access_token)

        database = user_notion.databases.retrieve(db_id)
        supported_properties = {
            prop_name: prop
            for prop_name, prop in database['properties'].items()
            if prop['type'] in self.SUPPORTED_PROPERTY_TYPES
        }
        property_buttons = []

        for prop_name, _ in supported_properties.items():
            button = InlineKeyboardButton(
                prop_name,
                callback_data=ChoosePropertyCallback.new(prop_name=prop_name),
            )
            property_buttons.append([button])

        done_button = InlineKeyboardButton(
            "Done selecting✅",
            callback_data=DonePropertySelectingCallback.new(),
        )
        property_buttons.append([done_button])

        markup = InlineKeyboardMarkup(inline_keyboard=property_buttons)

        props_list_message = await self._bot.send_message(
            chat_id,
            "Choose the properties you want to track:",
            reply_markup=markup,
        )
        await self._storage.add_temporaty_message_id(chat_id, props_list_message.message_id)

        instruction_message = await self._bot.send_message(
            chat_id,
            "Press 'Done selecting✅' when you're finished selecting properties🤖",
        )
        await self._storage.add_temporaty_message_id(chat_id, instruction_message.message_id)

        tracked_properties = await self._storage.get_user_tracked_properties(message.chat.id)
        if tracked_properties:
            text = f"Current tracked properties: {', '.join(tracked_properties)}"
        else:
            text = "No properties have been selected."

        sent_message = await self._bot.send_message(chat_id, text=text)
        await self._storage.set_tracked_properties_message_id(chat_id, sent_message.message_id)
        await self._storage.add_temporaty_message_id(chat_id, sent_message.message_id)

    async def handle_callback(self, query: CallbackQuery) -> None:
        chat_id = query.message.chat.id
        data = ChoosePropertyCallback.parse(query.data)
        prop_name = data.get("prop_name")
        tracked_properties = await self._storage.get_user_tracked_properties(query.message.chat.id)

        if not tracked_properties:
            tracked_properties = []

        if prop_name not in tracked_properties:
            tracked_properties.append(prop_name)
        else:
            tracked_properties.remove(prop_name)

        await self._storage.set_user_tracked_properties(query.message.chat.id, tracked_properties)

        if tracked_properties:
            new_text = f"Current tracked properties: {', '.join(tracked_properties)}"
        else:
            new_text = "No properties have been selected."

        message_id = await self._storage.get_tracked_properties_message_id(chat_id)
        if not message_id:
            sent_message = await self._bot.send_message(
                chat_id,
                text=new_text,
            )
            await self._storage.set_tracked_properties_message_id(chat_id, sent_message.message_id)
            await self._storage.add_temporaty_message_id(chat_id, sent_message.message_id)
        else:
            try:
                await self._bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=new_text,
                )
            except (exceptions.MessageNotModified, exceptions.MessageToEditNotFound):
                pass

    async def handle_finish(self, query: CallbackQuery) -> None:
        chat_id = query.message.chat.id
        tracked_properties = await self._storage.get_user_tracked_properties(query.message.chat.id)

        sent_message_id = await self._storage.get_tracked_properties_message_id(chat_id)
        if sent_message_id:
            await self._delete_tracked_properties_message(chat_id, sent_message_id)

        await self.remove_temporary_messages(chat_id)
        if not tracked_properties:
            sent_message = await self._bot.send_message(
                chat_id,
                "No properties have been selected. Please choose at least one property.",
            )
            await self._storage.add_temporaty_message_id(chat_id, sent_message.message_id)
            await self.execute(query.message)
            return None
        else:
            await self._bot.send_message(
                chat_id,
                f"Properties being tracked: {', '.join(tracked_properties)}",
            )
            await self.execute_next_if_applicable(query.message)

    async def _delete_tracked_properties_message(self, chat_id: int, sent_message_id: int) -> None:
        try:
            await self._bot.delete_message(chat_id, sent_message_id)
        except (exceptions.MessageToDeleteNotFound, exceptions.MessageCantBeDeleted):
            pass
        await self._storage.delete_tracked_properties_message_id(chat_id)
