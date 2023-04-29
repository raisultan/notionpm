from aiogram import Dispatcher, types

from app.initializer import bot

from app.commands.start import send_welcome
from app.commands.connect_notion import send_login_url
from app.commands.choose_database import ChooseDatabaseCallback, ChooseDatabaseCommand
from app.commands.choose_properties import ChoosePropertyCallback, ChoosePropertiesCommand
from app.commands.set_notifications import set_notification_handler, set_notification_callback_handler, set_notification_callback_data, on_chat_member_updated

from app.initializer import bot
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


def setup_dispatcher():
    dp = Dispatcher(bot)

    dp.register_message_handler(
        send_welcome,
        commands=["start"],
    )
    dp.register_message_handler(
        send_login_url,
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
        set_notification_handler,
        commands=["set_notification"],
    )
    dp.register_callback_query_handler(
        set_notification_callback_handler,
        set_notification_callback_data.filter(),
    )
    dp.register_message_handler(
        on_chat_member_updated,
        content_types=[types.ContentType.NEW_CHAT_MEMBERS],
    )

    return dp
