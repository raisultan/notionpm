import re

from aiogram import Bot, Dispatcher
from aiogram.dispatcher.filters import Regexp
from aiogram.types import ContentType
from aiohttp.web import Application
from redis.asyncio import ConnectionPool, Redis

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
from app.middleware import ForceUserSetupMiddleware
from app.notion import NotionClient
from app.storage import Storage
from v0_1.notion_oauth import NotionOAuth



async def redis(app: Application):
    pool = ConnectionPool.from_url("redis://localhost:6379")
    app['redis'] = Redis(connection_pool=pool)
    yield
    await pool.disconnect()


async def bot(app: Application):
    app['bot'] = Bot(token=app['config']['bot_token'])
    yield
    await app['bot'].close()


async def storage(app: Application):
    app['storage'] = Storage(redis)


async def notion_oauth(app: Application):
    app['notion_oauth'] = NotionOAuth(
        storage=storage,
        client_id=app['config']['notion_client_id'],
        client_secret=app['config']['notion_client_secret'],
        redirect_uri=app['config']['notion_redirect_uri'],
    )


async def dispatcher(app: Application):
    app['dispatcher'] = Dispatcher(app['bot'])


async def commands(app: Application):
    toggle_notifications = ToggleNotificationsCommand(
        bot=app['bot'],
        storage=app['storage'],
    )
    setup_notifications = SetupNotificationsCommand(
        bot=app['bot'],
        next=toggle_notifications,
        storage=app['storage'],
    )
    choose_properties = ChoosePropertiesCommand(
        bot=app['bot'],
        next=setup_notifications,
        storage=app['storage'],
        notion=NotionClient,
    )
    choose_database = ChooseDatabaseCommand(
        bot=app['bot'],
        next=choose_properties,
        storage=app['storage'],
        notion=NotionClient,
    )
    connect_notion = ConnectNotionCommand(
        bot=app['bot'],
        next=choose_database,
        storage=app['storage'],
        notion_oauth=app['notion_oauth'],
    )
    start = StartCommand(app['bot'])

    app['connect_notion'] = connect_notion
    app['dispatcher'].register_message_handler(
        start.execute,
        commands=["start"],
    )
    app['dispatcher'].register_message_handler(
        connect_notion.execute,
        commands=["login"],
    )
    app['dispatcher'].register_message_handler(
        choose_database.execute,
        commands=["choose_database"],
    )
    app['dispatcher'].register_callback_query_handler(
        choose_database.handle_callback,
        ChooseDatabaseCallback.filter()
    )
    app['dispatcher'].register_message_handler(
        choose_properties.execute,
        commands=["choose_properties"],
    )
    app['dispatcher'].register_callback_query_handler(
        choose_properties.handle_callback,
        ChoosePropertyCallback.filter(),
    )
    app['dispatcher'].register_callback_query_handler(
        choose_properties.handle_finish,
        DonePropertySelectingCallback.filter(),
    )
    app['dispatcher'].register_message_handler(
        setup_notifications.execute,
        commands=["set_notification"],
    )
    app['dispatcher'].register_callback_query_handler(
        setup_notifications.handle_private_messages,
        SetupNotificationsCallback.filter(),
    )
    app['dispatcher'].register_message_handler(
        setup_notifications.handle_group_chat,
        content_types=[ContentType.NEW_CHAT_MEMBERS],
    )
    toggle_notifications_pattern = re.compile(
        r'^(Pause notifications ⏸️|Unpause notifications ⏯️)$',
        re.IGNORECASE
    )
    app['dispatcher'].message_handler(
        Regexp(toggle_notifications_pattern)
    )(toggle_notifications.execute)

    setup_commands = (
        connect_notion,
        choose_database,
        choose_properties,
        setup_notifications,
    )
    app['dispatcher'].middleware.setup(ForceUserSetupMiddleware(bot, setup_commands))
