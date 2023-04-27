import asyncio
import os
import signal

from aiogram import Bot, Dispatcher, types
from aiogram.utils import exceptions
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ParseMode,
    ReplyKeyboardMarkup,
)
from aiogram.utils.callback_data import CallbackData
from aiohttp import web
from aiohttp.web_request import Request
from dotenv import load_dotenv
from notion_client import Client as NotionCLI

import app.storage as storage
from app.notion import list_databases
from app.notifications import app as notification_app

from v0_1.notion_oauth import NotionOAuth


load_dotenv()

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher(bot)

NOTION_CLIENT_ID = os.environ["NOTION_CLIENT_ID"]
NOTION_CLIENT_SECRET = os.environ["NOTION_CLIENT_SECRET"]
NOTION_REDIRECT_URI = os.environ["NOTION_REDIRECT_URI"]
BOT_URL = os.environ["BOT_URL"]

notion_oauth = NotionOAuth(
    storage=storage,
    client_id=NOTION_CLIENT_ID,
    client_secret=NOTION_CLIENT_SECRET,
    redirect_uri=NOTION_REDIRECT_URI,
)

SUPPORTED_PROPERTY_TYPES = [
    'title',
    'status',
    'date',
    'people',
    'url',
]


async def handle_oauth(request: Request):
    chat_id = await notion_oauth.handle_oauth(request)
    if chat_id:
        message = types.Message(chat=types.Chat(id=int(chat_id), type='private'))
        await skip_or_continue_setup(message)
        return web.HTTPFound(BOT_URL)
    else:
        return web.Response(status=400)


async def skip_or_continue_setup(message: types.Message):
    access_token = await storage.get_user_access_token(message.chat.id)
    if not access_token:
        await send_login_url(message)
        await storage.set_user_setup_status(message.chat.id, True)
        return

    db_id = await storage.get_user_db_id(message.chat.id)
    if not db_id:
        await choose_database_handler(message)
        await storage.set_user_setup_status(message.chat.id, True)
        return

    tracked_properties = await storage.get_user_tracked_properties(message.chat.id)
    if not tracked_properties:
        await choose_properties_handler(message)
        await storage.set_user_setup_status(message.chat.id, True)
        return

    await storage.set_user_setup_status(message.chat.id, False)


async def send_welcome(message: types.Message):
    if message.chat.type == "private":
        await skip_or_continue_setup(message)
    else:
        pass


async def send_login_url(message: types.Message):
    login_url = (
        "https://api.notion.com/v1/oauth/authorize"
        f"?client_id={NOTION_CLIENT_ID}"
        f"&redirect_uri={NOTION_REDIRECT_URI}"
        f"&response_type=code"
        f"&state=instance-{message.chat.id}"
    )

    button = types.InlineKeyboardButton(text="Connect Notion📖", url=login_url)
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[button]])
    reply = f"Connect your Notion workspace"

    connect_message = await bot.send_message(
        message.chat.id,
        reply,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
    )
    await storage.set_connect_message_id(message.chat.id, connect_message.message_id)


choose_db_callback_data = CallbackData("choose_db", "db_id", "db_title")
async def choose_database_handler(message: types.Message):
    chat_id = message.chat.id
    access_token = await storage.get_user_access_token(chat_id)

    if not access_token:
        await bot.send_message(
            chat_id,
            "You need to connect your Notion workspace first. Use the /login command to connect.",
        )
        return

    user_notion = NotionCLI(auth=access_token)
    databases = list_databases(user_notion)

    if not databases:
        await bot.send_message(message.chat.id, "No databases found in your Notion workspace.")
        return

    connect_message_id = await storage.get_connect_message_id(message.chat.id)
    if connect_message_id:
        await bot.delete_message(chat_id, connect_message_id)

    if len(databases) == 1:
        db = databases[0]
        await storage.set_user_db_id(message.chat.id, db.id)
        await bot.send_message(
            message.chat.id,
            f"Yeah, default database has been set to {db.title} 🎉",
        )
        await skip_or_continue_setup(message)
        return

    inline_keyboard = []

    for db in databases:
        button = InlineKeyboardButton(
            db.title,
            callback_data=choose_db_callback_data.new(db_id=db.id, db_title=db.title),
        )
        inline_keyboard.append([button])

    markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    current_db_id = await storage.get_user_db_id(message.chat.id)
    if current_db_id:
        text = (
            "You have already chosen a default database. "
            "You can choose a new one from the list below:"
        )
        await bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        await bot.send_message(
            message.chat.id,
            "Choose the default database for team tasks:",
            reply_markup=markup,
        )


async def choose_db_callback_handler(callback_query: CallbackQuery, callback_data: dict):
    db_id = callback_data.get("db_id")
    chat_id = callback_query.message.chat.id

    await storage.set_user_db_id(chat_id, db_id)
    await bot.send_message(
        chat_id,
        f"Default database has been set to {callback_data.get('db_title')} 🎉",
    )
    await skip_or_continue_setup(callback_query.message)


choose_property_callback_data = CallbackData("choose_property", "prop_name")
async def choose_properties_handler(message: types.Message):
    chat_id = message.chat.id
    access_token = await storage.get_user_access_token(chat_id)

    sent_message_id = await storage.get_tracked_properties_message_id(chat_id)
    if sent_message_id:
        await bot.delete_message(chat_id, sent_message_id)
        await storage.delete_tracked_properties_message_id(chat_id)

    if not access_token:
        await bot.send_message(
            chat_id,
            "You need to connect your Notion workspace first. Use the /login command to connect.",
        )
        return

    user_notion = NotionCLI(auth=access_token)
    db_id = await storage.get_user_db_id(chat_id)

    if not db_id:
        await bot.send_message(
            chat_id,
            "You must choose a default database first. Use the /choose_database command.",
        )
        return

    database = user_notion.databases.retrieve(db_id)
    supported_properties = {
        prop_name: prop
        for prop_name, prop in database['properties'].items()
        if prop['type'] in SUPPORTED_PROPERTY_TYPES
    }
    property_buttons = []

    for prop_name, _ in supported_properties.items():
        button = InlineKeyboardButton(
            prop_name,
            callback_data=choose_property_callback_data.new(prop_name=prop_name),
        )
        property_buttons.append([button])

    markup = InlineKeyboardMarkup(inline_keyboard=property_buttons)

    done_button = KeyboardButton("Done selecting✅")
    done_markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    done_markup.add(done_button)

    await bot.send_message(
        chat_id,
        "Choose the properties you want to track:",
        reply_markup=markup,
    )

    await bot.send_message(
        chat_id,
        "Press 'Done selecting✅' when you're finished selecting properties🤖",
        reply_markup=done_markup,
    )


async def properties_done_handler(message: types.Message):
    chat_id = message.chat.id
    tracked_properties = await storage.get_user_tracked_properties(chat_id)

    sent_message_id = await storage.get_tracked_properties_message_id(chat_id)
    if sent_message_id:
        await bot.delete_message(chat_id, sent_message_id)
        await storage.delete_tracked_properties_message_id(chat_id)

    if not tracked_properties:
        await bot.send_message(
            chat_id,
            "No properties have been selected. Please choose at least one property.",
        )
        await choose_properties_handler(message)
    else:
        await bot.send_message(
            chat_id,
            f"Selected properties: {', '.join(tracked_properties)}",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        is_in_setup = await storage.get_user_setup_status(chat_id)
        if is_in_setup:
            await bot.send_message(
                chat_id,
                "Congratulations! 🎉 Your setup process is complete. "
                "You can now start tracking changes in your Notion workspace.",
            )
            await storage.set_user_setup_status(chat_id, False)


async def choose_property_callback_handler(callback_query: CallbackQuery, callback_data: dict):
    chat_id = callback_query.message.chat.id
    prop_name = callback_data.get("prop_name")
    tracked_properties = await storage.get_user_tracked_properties(chat_id)

    if not tracked_properties:
        tracked_properties = []

    if prop_name not in tracked_properties:
        tracked_properties.append(prop_name)
    else:
        tracked_properties.remove(prop_name)

    await storage.set_user_tracked_properties(chat_id, tracked_properties)

    if tracked_properties:
        new_text = f"Current tracked properties: {', '.join(tracked_properties)}"
    else:
        new_text = "No properties have been selected."

    message_id = await storage.get_tracked_properties_message_id(chat_id)
    if not message_id:
        sent_message = await bot.send_message(
            chat_id,
            text=new_text,
        )
        await storage.set_tracked_properties_message_id(chat_id, sent_message.message_id)
    else:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=new_text,
            )
        except exceptions.MessageNotModified:
            pass


set_notification_callback_data = CallbackData("set_notification", "notification_type")
async def set_notification_handler(message: types.Message):
    chat_id = message.chat.id
    bot_username = (await bot.me).username
    add_to_group_url = f"https://t.me/{bot_username}?startgroup=0"

    print(f'FROM USER MEMBER: {message.from_user.id}')

    private_button = types.InlineKeyboardButton(
        "Stay here 👨‍💻",
        callback_data=set_notification_callback_data.new(notification_type="private")
    )
    group_button = types.InlineKeyboardButton(
        "Track in group chat 👥",
        url=add_to_group_url,
    )
    markup = types.InlineKeyboardMarkup(inline_keyboard=[[private_button, group_button]])

    await bot.send_message(
        chat_id,
        "Choose where you would like to receive notifications:",
        reply_markup=markup,
    )


async def set_notification_callback_handler(callback_query: CallbackQuery, callback_data: dict):
    chat_id = callback_query.message.chat.id
    notification_type = callback_data.get("notification_type")

    if notification_type == "private":
        await storage.set_user_notification_type(chat_id, "private")
        await storage.set_user_notification_chat_id(callback_query.from_user.id, chat_id)
        await bot.send_message(
            chat_id,
            "Roger that! I will send you notifications in this chat 🤖",
        )
    else:
        await bot.send_message(chat_id, "Something went wrong, please try again 🥺")

async def on_chat_member_updated(message: types.Message):
    chat_id = message.chat.id
    from_user_id = message.from_user.id
    bot_user = await bot.me

    if message.new_chat_members[0].is_bot and message.new_chat_members[0].id == bot_user.id:
        await storage.set_user_notification_type(from_user_id, "group")
        await storage.set_user_notification_chat_id(from_user_id, chat_id)

        await bot.send_message(
            chat_id,
            "Great! Notifications will be sent to this group chat. 🎉",
        )
    else:
        return


dp.register_message_handler(
    send_welcome,
    commands=["start"],
)
dp.register_message_handler(
    send_login_url,
    commands=["login"],
)
dp.register_message_handler(
    choose_database_handler,
    commands=["choose_database"],
)
dp.register_callback_query_handler(
    choose_db_callback_handler,
    choose_db_callback_data.filter()
)
dp.register_message_handler(
    choose_properties_handler,
    commands=["choose_properties"],
)
dp.register_callback_query_handler(
    choose_property_callback_handler,
    choose_property_callback_data.filter(),
)
dp.register_message_handler(
    properties_done_handler,
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


async def main():
    global app
    app = web.Application()
    app.add_routes([web.get("/oauth/callback", handle_oauth)])

    global runner
    runner = web.AppRunner(app)
    await runner.setup()

    global tcp_server
    tcp_server = web.TCPSite(runner, "localhost", 8080)

    global notification_app
    notification_app = asyncio.create_task(notification_app.session.scheduler.serve())

    await tcp_server.start()
    await dp.start_polling()


async def shutdown(signal, loop):
    print(f"\nReceived {signal.name} signal, shutting down...")
    notification_app.cancel()

    dp.stop_polling()
    await dp.wait_closed()
    await bot.close()

    await tcp_server.stop()
    await runner.cleanup()
    await app.cleanup()
    await loop.shutdown_asyncgens()
    loop.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    for signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signal, lambda s=signal: asyncio.create_task(shutdown(s, loop)))

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
        print("Application has been shut down.")
