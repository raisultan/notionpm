import asyncio
import base64
import os

import aiohttp
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


load_dotenv()

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher(bot)

NOTION_CLIENT_ID = os.environ["NOTION_CLIENT_ID"]
NOTION_CLIENT_SECRET = os.environ["NOTION_CLIENT_SECRET"]
NOTION_REDIRECT_URI = os.environ["NOTION_REDIRECT_URI"]
BOT_URL = os.environ["BOT_URL"]

SUPPORTED_PROPERTY_TYPES = [
    'title',
    'status',
    'date',
    'people',
    'url',
]


async def make_oauth_request(code: str):
    auth_creds = f"{NOTION_CLIENT_ID}:{NOTION_CLIENT_SECRET}"
    encoded_auth_creds = base64.b64encode(auth_creds.encode("ascii")).decode("ascii")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_auth_creds}",
    }
    json = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": NOTION_REDIRECT_URI,
    }

    http_client = aiohttp.ClientSession()
    response = await http_client.post(
        "https://api.notion.com/v1/oauth/token",
        json=json,
        headers=headers,
    )
    return await response.json()


async def handle_oauth(request: Request):
    code = request.query.get("code")
    state = request.query.get("state")
    if state and "-" in state:
        chat_id = state.split("-")[1]
    else:
        chat_id = None

    if not (code and chat_id):
        return web.Response(status=400)

    try:
        response = await make_oauth_request(code)

        access_token = response.get("access_token")
        notion = NotionCLI(auth=access_token)
        blocks = notion.search()
        print(blocks)

        await storage.save_user_access_token(chat_id, access_token)

        message = types.Message(chat=types.Chat(id=int(chat_id), type='private'))
        await check_and_continue_setup(message)
        return web.HTTPFound(BOT_URL)
    except Exception as e:
        print(e)
        return web.Response(status=400)


async def check_and_continue_setup(message: types.Message):
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
    await check_and_continue_setup(message)


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
    await bot.send_message(
        message.chat.id,
        reply,
        reply_markup=markup,
        parse_mode=ParseMode.HTML,
    )


choose_db_callback_data = CallbackData("choose_db", "db_id", "db_title")
async def choose_database_handler(message: types.Message):
    access_token = await storage.get_user_access_token(message.chat.id)

    if not access_token:
        await bot.send_message(
            message.chat.id,
            "You need to connect your Notion workspace first. Use the /login command to connect.",
        )
        return

    user_notion = NotionCLI(auth=access_token)
    databases = list_databases(user_notion)

    if not databases:
        await bot.send_message(message.chat.id, "No databases found in your Notion workspace.")
        return

    if len(databases) == 1:
        db = databases[0]
        await storage.set_user_db_id(message.chat.id, db.id)
        await bot.send_message(
            message.chat.id,
            f"Default database has been set to {db.title} 🎉",
        )
        await check_and_continue_setup(message)
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
    await check_and_continue_setup(callback_query.message)


choose_property_callback_data = CallbackData("choose_property", "prop_name")
async def choose_properties_handler(message: types.Message):
    chat_id = message.chat.id
    access_token = await storage.get_user_access_token(chat_id)

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
    
    if not tracked_properties:
        await bot.send_message(chat_id, "No properties have been selected. Please choose at least one property.")
        await choose_properties_handler(message)
    else:
        sent_message_id = await storage.get_tracked_properties_message_id(chat_id)

        if sent_message_id:
            await bot.delete_message(chat_id, sent_message_id)
            await storage.delete_tracked_properties_message_id(chat_id)

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


dp.register_message_handler(send_welcome, commands=["start"])
dp.register_message_handler(send_login_url, commands=["login"])
dp.register_message_handler(choose_database_handler, commands=["choose_database"])
dp.register_callback_query_handler(
    choose_db_callback_handler, choose_db_callback_data.filter()
)
dp.register_message_handler(choose_properties_handler, commands=["choose_properties"])
dp.register_callback_query_handler(
    choose_property_callback_handler, choose_property_callback_data.filter()
)
dp.register_message_handler(properties_done_handler, lambda message: message.text == 'Done selecting✅')


tcp_server = None
notification_task = None

async def main():
    app = web.Application()
    app.add_routes([web.get("/oauth/callback", handle_oauth)])
    runner = web.AppRunner(app)
    await runner.setup()
    tcp_server = web.TCPSite(runner, "localhost", 8080)

    asyncio.create_task(notification_app.session.scheduler.serve())
    await tcp_server.start()
    await dp.start_polling()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Received Ctrl+C, shutting down...")
        loop.run_until_complete(dp.stop_polling())
        loop.run_until_complete(tcp_server.stop())
        loop.run_until_complete(notification_task.cancel())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        print("Application has been shut down.")
