from aiogram import Bot, Dispatcher
from aiogram.types import Message, ContentType
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
    def __init__(self, bot: Bot):
        super().__init__()
        self._bot = bot

    async def on_pre_process_message(self, message: Message, data: dict):
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

    dp.middleware.setup(ForceUserSetupMiddleware(bot))

    return dp
