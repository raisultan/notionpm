import os

from aiogram import Bot
from dotenv import load_dotenv

import app.storage as storage
from v0_1.notion_oauth import NotionOAuth

load_dotenv()


NOTION_CLIENT_ID = os.environ["NOTION_CLIENT_ID"]
NOTION_CLIENT_SECRET = os.environ["NOTION_CLIENT_SECRET"]
NOTION_REDIRECT_URI = os.environ["NOTION_REDIRECT_URI"]
BOT_URL = os.environ["BOT_URL"]

bot = Bot(token=os.environ["BOT_TOKEN"])

notion_oauth = NotionOAuth(
    storage=storage,
    client_id=NOTION_CLIENT_ID,
    client_secret=NOTION_CLIENT_SECRET,
    redirect_uri=NOTION_REDIRECT_URI,
)
