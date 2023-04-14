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

        await bot.send_message(
            chat_id,
            "<b>Notion workspace connected successfully!🎊🤖</b>",
            parse_mode=ParseMode.HTML
        )
        return web.HTTPFound(BOT_URL)
    except Exception as e:
        print(e)
        return web.Response(status=400)


async def send_welcome(message: types.Message):
    access_token = await storage.get_user_access_token(message.chat.id)
    if access_token:
        reply = (
            "Hi there!👋 Seems like you already connected your Notion workspace. "
            "Time to proceed with setup 🦆"
        )
        await bot.send_message(message.chat.id, reply)
    else:
        reply = (
            "Hi there!👋 I'm a bot that can help you with project managememnt in Notion. "
            "Let's get started by connecting your Notion workspace 🚀"
        )

        login_url = (
            "https://api.notion.com/v1/oauth/authorize"
            f"?client_id={NOTION_CLIENT_ID}"
            f"&redirect_uri={NOTION_REDIRECT_URI}"
            f"&response_type=code"
            f"&state=instance-{message.chat.id}"
        )

        button = types.InlineKeyboardButton(text="Connect Notion📖", url=login_url)
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[button]])
        await bot.send_message(
            message.chat.id,
            reply,
            reply_markup=markup,
            parse_mode=ParseMode.HTML,
        )


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


choose_db_callback_data = CallbackData("choose_db", "db_id")
async def choose_database_handler(message: types.Message):
    access_token = await storage.get_user_access_token(message.chat.id)
    
    if not access_token:
        await bot.send_message(message.chat.id, "You need to connect your Notion workspace first. Use the /login command to connect.")
        return

    user_notion = NotionCLI(auth=access_token)
    databases = list_databases(user_notion)

    if not databases:
        await bot.send_message(message.chat.id, "No databases found in your Notion workspace.")
        return

    inline_keyboard = []

    for db in databases:
        button = InlineKeyboardButton(db.title, callback_data=choose_db_callback_data.new(db_id=db.id))
        inline_keyboard.append([button])

    markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
    current_db_id = await storage.get_user_db_id(message.chat.id)
    if current_db_id:
        await bot.send_message(
            message.chat.id,
            "You have already chosen a default database. You can choose a new one from the list below:",
            reply_markup=markup
        )
    else:
        await bot.send_message(message.chat.id, "Choose the default database for team tasks:", reply_markup=markup)


async def choose_db_callback_handler(callback_query: CallbackQuery, callback_data: dict):
    db_id = callback_data.get("db_id")
    chat_id = callback_query.message.chat.id

    await storage.set_user_db_id(chat_id, db_id)
    await bot.send_message(chat_id, f"Default database has been set to {callback_data.get('db_title')} 🎉")


dp.register_message_handler(send_welcome, commands=["start"])
dp.register_message_handler(send_login_url, commands=["login"])
dp.register_message_handler(choose_database_handler, commands=["choose_database"])
dp.register_callback_query_handler(
    choose_db_callback_handler, choose_db_callback_data.filter()
)


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
