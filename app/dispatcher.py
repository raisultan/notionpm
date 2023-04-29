from aiogram import Dispatcher, types

from app.initializer import bot

from app.commands.start import StartCommand
from app.commands.connect_notion import ConnectNotionCommand
from app.commands.choose_database import ChooseDatabaseCallback, ChooseDatabaseCommand
from app.commands.choose_properties import ChoosePropertyCallback, ChoosePropertiesCommand
from app.commands.set_notifications import SetupNotificationsCallback, SetupNotificationsCommand

from app.initializer import bot, notion_oauth
import app.storage as storage
from notion_client import Client as NotionCLI
import app.notion as notion_cli

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
connect_notion = ConnectNotionCommand(
    bot=bot,
    storage=storage,
    notion_oauth=notion_oauth,
)
start = StartCommand()
setup_notifications = SetupNotificationsCommand(
    bot=bot,
    storage=storage,
)


def setup_dispatcher():
    dp = Dispatcher(bot)

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
    dp.register_message_handler(
        choose_properties.handle_finish,
        lambda message: message.text == 'Done selecting✅',
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
        content_types=[types.ContentType.NEW_CHAT_MEMBERS],
    )

    return dp
