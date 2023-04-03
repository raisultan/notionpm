import asyncio
import base64
import os

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiohttp import web
from aiohttp.web_request import Request
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher(bot)
notion = Client(auth=os.environ["NOTION_KEY"])

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
        notion = Client(auth=access_token)
        blocks = notion.search()
        print(blocks)

        await bot.send_message(chat_id, "Login successful!")
        return web.HTTPFound(BOT_URL)
    except Exception as e:
        print(e)
        return web.Response(status=400)


async def send_welcome(message: types.Message):
    reply = (
        "Hi there! I'm a bot that can help you with Notion "
        "OAuth login. Just type /login to get started."
    )
    await bot.send_message(message.chat.id, reply)


async def send_login_url(message: types.Message):
    login_url = (
        "https://api.notion.com/v1/oauth/authorize"
        f"?client_id={NOTION_CLIENT_ID}"
        f"&redirect_uri={NOTION_REDIRECT_URI}"
        f"&response_type=code"
        f"&state=instance-{message.chat.id}"
    )
    reply = f"Click the link to login to Notion:\n\n{login_url}"
    await bot.send_message(message.chat.id, reply, parse_mode=ParseMode.HTML)


dp.register_message_handler(send_welcome, commands=["start"])
dp.register_message_handler(send_login_url, commands=["login"])


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
