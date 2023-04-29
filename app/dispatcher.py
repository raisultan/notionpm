from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.middlewares import BaseMiddleware

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

start = StartCommand(bot)
choose_database = ChooseDatabaseCommand(
    bot=bot,
    storage=storage,
    notion=NotionCLI,
    notion_cli=notion_cli,
)
connect_notion = ConnectNotionCommand(
    bot=bot,
    storage=storage,
    notion_oauth=notion_oauth,
    next=choose_database,
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


class ForceUserSetupMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot):
        super().__init__()
        self._bot = bot

    async def on_pre_process_message(self, message: types.Message, data: dict):
        if (
            not await connect_notion.is_finished(message)
            and await connect_notion.is_applicable(message)
        ):
            await connect_notion.execute(message)
        if (
            not await choose_database.is_finished(message)
            and await choose_database.is_applicable(message)
        ):
            await choose_database.execute(message)
        if (
            not await choose_properties.is_finished(message)
            and await choose_properties.is_applicable(message)
        ):
            await choose_properties.execute(message)
        if (
            not await setup_notifications.is_finished(message)
            and await setup_notifications.is_applicable(message)
        ):
            await setup_notifications.execute(message)


def setup_dispatcher():
    dp = Dispatcher(bot)

    dp.middleware.setup(ForceUserSetupMiddleware(bot))

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
        content_types=[types.ContentType.NEW_CHAT_MEMBERS],
    )

    return dp
