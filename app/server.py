import asyncio
import base64
import os

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from aiogram.utils.callback_data import CallbackData
from aiohttp import web
from aiohttp.web_request import Request
from dotenv import load_dotenv
from notion_client import Client as NotionCLI

import app.storage as storage
from app.notion import list_databases

load_dotenv()

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher(bot)

NOTION_CLIENT_ID = os.environ["NOTION_CLIENT_ID"]
NOTION_CLIENT_SECRET = os.environ["NOTION_CLIENT_SECRET"]
NOTION_REDIRECT_URI = os.environ["NOTION_REDIRECT_URI"]
BOT_URL = os.environ["BOT_URL"]


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
        return

    db_id = await storage.get_user_db_id(message.chat.id)
    if not db_id:
        await choose_database_handler(message)
        return

    tracked_properties = await storage.get_user_tracked_properties(message.chat.id)
    if not tracked_properties:
        await choose_properties_handler(message)
        return

    reply = (
        "Congratulations!🎉 You have completed the setup. "
        "Now you can manage your tasks in Notion. 🦆"
    )
    await bot.send_message(message.chat.id, reply)


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

    inline_keyboard = []

    for db in databases:
        button = InlineKeyboardButton(
            db.title,
            callback_data=choose_db_callback_data.new(db_id=db.id,db_title=db.title),
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
    properties = database['properties']
    property_buttons = []

    for prop_name, _ in properties.items():
        button = InlineKeyboardButton(
            prop_name,
            callback_data=choose_property_callback_data.new(prop_name=prop_name),
        )
        property_buttons.append([button])

    done_button = InlineKeyboardButton(
        "Done selecting ✅", callback_data="properties_done"
    )
    property_buttons.append([done_button])

    markup = InlineKeyboardMarkup(inline_keyboard=property_buttons)
    sent_message = await bot.send_message(
        chat_id,
        "Choose the properties you want to track and press 'Done selecting ✅' when finished:",
        reply_markup=markup,
    )

    await storage.set_sent_message_id(chat_id, sent_message.message_id)


async def properties_done_callback_handler(callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    sent_message_id = await storage.get_sent_message_id(chat_id)

    if sent_message_id == message_id:
        await bot.delete_message(chat_id, message_id)
        await bot.send_message(
            chat_id,
            "Property selection is complete. You can continue with other setup steps or use the bot's features.",
        )
    else:
        await bot.answer_callback_query(
            callback_query.id,
            "The property selection message has already been removed. Please use the bot's features or other setup steps.",
        )


async def choose_property_callback_handler(callback_query: CallbackQuery, callback_data: dict):
    chat_id = callback_query.message.chat.id
    prop_name = callback_data.get("prop_name")
    tracked_properties = await storage.get_user_tracked_properties(chat_id)

    if not tracked_properties:
        tracked_properties = []

    if prop_name in tracked_properties:
        tracked_properties.remove(prop_name)
        action = "removed from"
    else:
        tracked_properties.append(prop_name)
        action = "added to"

    await storage.set_user_tracked_properties(chat_id, tracked_properties)
    await bot.send_message(
        chat_id,
        f"Property {prop_name} has been {action} the tracked properties.",
    )
    await check_and_continue_setup(callback_query.message)


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
dp.register_callback_query_handler(properties_done_callback_handler, text="properties_done")


async def main():
    app = web.Application()
    app.add_routes([web.get("/oauth/callback", handle_oauth)])
    runner = web.AppRunner(app)
    await runner.setup()
    tcp_server = web.TCPSite(runner, "localhost", 8080)

    await tcp_server.start()
    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
