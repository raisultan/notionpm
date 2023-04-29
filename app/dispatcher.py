from typing import Any, Awaitable, Optional

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.dispatcher.filters.builtin import Command
from aiogram.dispatcher.handler import CancelHandler

from app.initializer import bot

from app.commands.start import StartCommand
from app.commands.connect_notion import ConnectNotionCommand
from app.commands.choose_database import ChooseDatabaseCallback, ChooseDatabaseCommand
from app.commands.choose_properties import (
    ChoosePropertyCallback,
    ChoosePropertiesCommand,
    DonePropertySelectingCallback,
)
from app.commands.set_notifications import SetupNotificationsCallback, SetupNotificationsCommand

from app.initializer import bot, notion_oauth
import app.storage as storage
from notion_client import Client as NotionCLI
import app.notion as notion_cli
from app.commands.continuous import ContinuousCommand

start = StartCommand(bot)
choose_database = ChooseDatabaseCommand(
    bot=bot,
    storage=storage,
    notion=NotionCLI,
    notion_cli=notion_cli,
)
choose_properties = ChoosePropertiesCommand(
    bot=bot,
    storage=storage,
    notion=NotionCLI,
)
setup_notifications = SetupNotificationsCommand(
    bot=bot,
    storage=storage,
)

continuous_choose_database = ContinuousCommand(
    command=choose_database,
    finish=choose_database.handle_callback,
    next=choose_properties,
)
continuous_choose_properties = ContinuousCommand(
    command=choose_properties,
    finish=choose_properties.handle_finish,
    next=setup_notifications,
)
connect_notion = ConnectNotionCommand(
    bot=bot,
    storage=storage,
    notion_oauth=notion_oauth,
    next=choose_database,
)


class ForceUserSetupMiddleware(BaseMiddleware):
    def __init__(self, dp: Dispatcher, bot: Bot, storage: Any):
        super().__init__()
        self._bot = bot
        self._dp = dp
        self._storage = storage

    async def on_pre_process_message(self, message: Message, data: dict):
        if self.is_registered_command(message):
            await self._storage.set_on_command(message.chat.id, message.text[1:])

        if (
            not await connect_notion.is_finished(message)
            and await connect_notion.is_applicable(message)
        ):
            await self._bot.send_message(
                message.chat.id,
                "Oops, seems like you haven't setup me yet. Let's do that 😇"
            )
            await connect_notion.execute(message)
            raise CancelHandler()
        if (
            not await choose_database.is_finished(message)
            and await choose_database.is_applicable(message)
        ):
            await self._bot.send_message(
                message.chat.id,
                "Oops, seems like you haven't setup me yet. Let's do that 😇"
            )
            await choose_database.execute(message)
            raise CancelHandler()
        if (
            not await choose_properties.is_finished(message)
            and await choose_properties.is_applicable(message)
        ):
            await self._bot.send_message(
                message.chat.id,
                "Oops, seems like you haven't setup me yet. Let's do that 😇"
            )
            await choose_properties.execute(message)
            raise CancelHandler()
        if (
            not await setup_notifications.is_finished(message)
            and await setup_notifications.is_applicable(message)
        ):
            await self._bot.send_message(
                message.chat.id,
                "Oops, seems like you haven't setup me yet. Let's do that 😇"
            )
            await setup_notifications.execute(message)
            raise CancelHandler()

    async def on_post_process_callback_query(
        self,
        query: CallbackQuery,
        result: Any,
        data: dict,
    ) -> None:
        on_command = await self._storage.get_on_command(query.message.chat.id)
        print('\n\n\n')
        print(f'On command: {on_command}')
        print('\n\n\n')
        if on_command:
            on_command_handler = self.get_command(on_command)
            print('\n\n\n')
            print(f'On command handler: {on_command_handler}')
            print('\n\n\n')
            await on_command_handler(query.message)

    def is_registered_command(self, message: Message) -> bool:
        command_prefix = "/"
        commands = [
            cmd
            for handler in self._dp.message_handlers.handlers
            if isinstance(handler, Command)
            for cmd in handler.names
        ]
        return message.text.startswith(command_prefix) and message.text[1:] in commands

    def get_command(self, command: str) -> Optional[Awaitable]:
        for handler in self._dp.message_handlers.handlers:
            if isinstance(handler, Command) and command in handler.names:
                return handler.callback
        return None


async def send_emojis_command(message: Message):
    emojis = "😀 😃 😄 😁 😆"
    await bot.send_message(
        message.chat.id,
        emojis,
    )


def setup_dispatcher():
    dp = Dispatcher(bot)

    dp.register_message_handler(send_emojis_command, commands=["emojis"])
    dp.register_message_handler(
        start.execute,
        commands=["start"],
    )
    dp.register_message_handler(
        connect_notion.execute,
        commands=["login"],
    )
    dp.register_message_handler(
        continuous_choose_database.command.execute,
        commands=["choose_database"],
    )
    dp.register_callback_query_handler(
        continuous_choose_database.finish,
        ChooseDatabaseCallback.filter()
    )
    dp.register_message_handler(
        continuous_choose_properties.command.execute,
        commands=["choose_properties"],
    )
    dp.register_callback_query_handler(
        continuous_choose_properties.command.handle_callback,
        ChoosePropertyCallback.filter(),
    )
    dp.register_callback_query_handler(
        continuous_choose_properties.finish,
        DonePropertySelectingCallback.filter(),
    )
    dp.register_message_handler(
        setup_notifications.execute,
        commands=["set_notification"],
    )
    dp.register_callback_query_handler(
        setup_notifications.handle_private_messages,
        SetupNotificationsCallback.filter(),
    )
    dp.register_message_handler(
        setup_notifications.handle_group_chat,
        content_types=[ContentType.NEW_CHAT_MEMBERS],
    )

    dp.middleware.setup(ForceUserSetupMiddleware(dp, bot, storage))

    return dp
