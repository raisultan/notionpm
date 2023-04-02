import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from notion_client import Client
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up Notion client
notion = Client(auth=os.environ["NOTION_KEY"])

# Set up Telegram bot
bot_token = os.environ["BOT_TOKEN"]
bot = Bot(token=bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())

# Set up Notion integration details
NOTION_CLIENT_ID = os.environ["OAUTH_CLIENT_ID"]
NOTION_CLIENT_SECRET = os.environ["OAUTH_CLIENT_SECRET"]
NOTION_REDIRECT_URI = os.environ["CALLBACK_URL"]

# Define state for the OAuth flow
class AuthState(FSMContext):
    pass

# Define start command for the bot
@dp.message_handler(commands=["start"])
async def start(message: types.Message, state: AuthState):
    # Generate URL to start OAuth flow
    params = {
        "client_id": NOTION_CLIENT_ID,
        "redirect_uri": NOTION_REDIRECT_URI,
        "response_type": "code",
        "scope": "read_write",
    }
    url = "https://api.notion.com/v1/oauth/authorize?" + urlencode(params)

    # Save state and send user to Notion login page
    await AuthState.start.set()
    await state.update_data(url=url)
    await message.answer(f"Please login to Notion using this link: {url}")

# Handle callback from Notion after user logs in
@dp.message_handler(regexp=r"code=[a-zA-Z0-9]+")
async def handle_notion_callback(message: types.Message, state: AuthState):
    # Extract authorization code from URL
    auth_code = message.text.split("=")[1]

    # Exchange authorization code for access token
    headers = {
        "Content-Type": "application/json",
        "Notion-Version": "2021-08-16",
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": NOTION_REDIRECT_URI,
        "client_id": NOTION_CLIENT_ID,
        "client_secret": NOTION_CLIENT_SECRET,
    }
    response = notion.oauth.token(**data)

    # Save access token and notify user
    access_token = response["access_token"]
    await message.answer("Login successful!")
    await state.finish()

# Handle incoming webhooks
async def handle_webhook(request):
    update = types.Update.parse_raw(await request.text())
    await dp.process_updates([update])
    return web.Response(text="ok")

# Start the bot and set up webhook
if __name__ == "__main__":
    from aiohttp import web
    from aiogram import executor

    # Set up webhook
    app = web.Application()
    app.router.add_post(f"/{bot_token}/webhook", handle_webhook)
    runner = web.AppRunner(app)
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=f"/{bot_token}/webhook",
        skip_updates=True,
        on_startup=runner.setup(),
        on_shutdown=runner.cleanup(),
    )
