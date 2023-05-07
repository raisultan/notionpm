import re

from aiogram import Dispatcher
from aiogram.dispatcher.filters import Regexp
from aiogram.types import Message, ContentType

from app.initializer import bot, storage

from app.commands.start import StartCommand
from app.commands.connect_notion import ConnectNotionCommand
from app.commands.choose_database import (
    ChooseDatabaseCallback,
    ChooseDatabaseCommand,
)
from app.commands.choose_properties import (
    ChoosePropertyCallback,
    ChoosePropertiesCommand,
    DonePropertySelectingCallback,
)
from app.commands.set_notifications import (
    SetupNotificationsCallback,
    SetupNotificationsCommand,
)
from app.commands.toggle_notifications import ToggleNotificationsCommand
from app.initializer import bot, notion_oauth
from app.middleware import ForceUserSetupMiddleware
from app.notion import NotionClient


async def send_emojis_command(message: Message):
    emojis = "😀 😃 😄 😁 😆"
    await bot.send_message(
        message.chat.id,
        emojis,
    )


def setup_dispatcher():
    toggle_notifications = ToggleNotificationsCommand(
        bot=bot,
        storage=storage,
    )
    setup_notifications = SetupNotificationsCommand(
        bot=bot,
        next=toggle_notifications,
        storage=storage,
    )
    choose_properties = ChoosePropertiesCommand(
        bot=bot,
        next=setup_notifications,
        storage=storage,
        notion=NotionClient,
    )
    choose_database = ChooseDatabaseCommand(
        bot=bot,
        next=choose_properties,
        storage=storage,
        notion=NotionClient,
    )
    connect_notion = ConnectNotionCommand(
        bot=bot,
        next=choose_database,
        storage=storage,
        notion_oauth=notion_oauth,
    )
    start = StartCommand(bot)

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
        choose_database.execute,
        commands=["choose_database"],
    )
    dp.register_callback_query_handler(
        choose_database.handle_callback,
        ChooseDatabaseCallback.filter()
    )
    dp.register_message_handler(
        choose_properties.execute,
        commands=["choose_properties"],
    )
    dp.register_callback_query_handler(
        choose_properties.handle_callback,
        ChoosePropertyCallback.filter(),
    )
    dp.register_callback_query_handler(
        choose_properties.handle_finish,
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
    toggle_notifications_pattern = re.compile(
        r'^(Pause notifications ⏸️|Unpause notifications ⏯️)$',
        re.IGNORECASE
    )
    dp.message_handler(Regexp(toggle_notifications_pattern))(toggle_notifications.execute)

    setup_commands = (
        connect_notion,
        choose_database,
        choose_properties,
        setup_notifications,
    )
    dp.middleware.setup(ForceUserSetupMiddleware(bot, setup_commands))

    return dp
