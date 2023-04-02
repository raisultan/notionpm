import os
from aiohttp import web
from aiohttp.web_request import Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.dispatcher.webhook import SendMessage
from dotenv import load_dotenv
from notion_client import Client
from aiogram.dispatcher import FSMContext
import aiohttp


load_dotenv()

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher(bot)
notion = Client(auth=os.environ["NOTION_KEY"])

NOTION_CLIENT_ID = os.environ["OAUTH_CLIENT_ID"]
NOTION_CLIENT_SECRET = os.environ["OAUTH_CLIENT_SECRET"]
NOTION_REDIRECT_URI = os.environ["CALLBACK_URL"]

import base64

class AuthState(FSMContext):
    pass

async def handle(request: Request):
    if request.method != 'GET':
        return web.Response(status=405)
    code = request.query.get("code")
    chat_id = request.query.get("state").split("-")[1]
    if code and chat_id:
        async with aiohttp.ClientSession() as session:
            # Exchange the authorization code for an access token
            json = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": NOTION_REDIRECT_URI,
            }
            credentials = f"{NOTION_CLIENT_ID}:{NOTION_CLIENT_SECRET}"
            credentials_bytes = credentials.encode("ascii")
            # Base64-encode the bytes object
            encoded_credentials_bytes = base64.b64encode(credentials_bytes)
            # Convert the encoded bytes object to a string
            encoded_credentials_str = encoded_credentials_bytes.decode("ascii")
            print(json)
            response = await session.post(
                "https://api.notion.com/v1/oauth/token",
                json=json,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {encoded_credentials_str}",
                },
            )
            data = await response.json()
            print('-------------------------')
            print(data)
            print('-------------------------')
            access_token = data.get("access_token")
            print('ACCESS TOKEN:')
            print(access_token)
            notion = Client(auth=access_token)
            blocks = notion.search()
            print(blocks)

            await bot.send_message(chat_id, 'Login successful!')

        return web.Response(status=200)
    return web.Response(status=400)

async def send_welcome(message: types.Message):
    await bot.send_message(message.chat.id, "Hi there! I'm a bot that can help you with Notion OAuth login. Just type /login to get started.")

async def send_login_url(message: types.Message):
    chat_id = message.chat.id
    login_url = f'https://api.notion.com/v1/oauth/authorize?client_id={NOTION_CLIENT_ID}&redirect_uri={NOTION_REDIRECT_URI}&response_type=code&state=instance-{chat_id}'
    await bot.send_message(message.chat.id, f'Click the link to login to Notion:\n\n{login_url}', parse_mode=ParseMode.HTML)

async def handle_notion_callback(message: types.Message):
    # Extract authorization code from URL
    auth_code = message.text.split("=")[1]

    notion = Client(auth=auth_code)
    await message.answer("Login successful!")

dp.register_message_handler(send_welcome, commands=['start'])
dp.register_message_handler(send_login_url, commands=['login'])
dp.register_message_handler(handle_notion_callback, regexp=r"code=[a-zA-Z0-9]+")

if __name__ == '__main__':
    async def main():
        app = web.Application()
        app.add_routes([web.get('/oauth/callback', handle)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()
        await dp.start_polling()

    # Run the main coroutine until it completes
    import asyncio
    asyncio.run(main())
