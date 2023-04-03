import os
from dataclasses import dataclass
from typing import NamedTuple

from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv
from notion_client import Client as NotionCLI

load_dotenv()

token = os.environ.get('NOTION_KEY')
db_id = os.environ.get('NOTION_DB_ID')
notion = NotionCLI(auth=token)
bot_token = os.environ.get('BOT_TOKEN')

bot = Bot(token=bot_token)
dp = Dispatcher(bot)


class Database(NamedTuple):
    id: str
    title: str


@dataclass
class Page:
    id: str
    title: str
    properties: dict


def list_databases(notion: NotionCLI) -> list[Database]:
    blocks = notion.search()
    databases = []

    for block in blocks['results']:
        # see search_example.py
        if block['object'] == 'database':
            databases.append(
                Database(
                    id=block['id'],
                    title=block['title'][0]['plain_text'],
                ),
            )

    return databases


def list_pages_from(notion: NotionCLI, db_id: str) -> list[Page]:
    blocks = notion.databases.query(db_id)
    pages = []

    for block in blocks['results']:
        pages.append(
            Page(
                id=block['id'],
                title=block['Name']['title'][0]['plain_text'],
                properties=block['properties'],
            )
        )
    return pages


@dp.message_handler(commands=['start'])
async def tg_start(message: types.Message):
    await message.answer("I'm here for you 🥷")


@dp.message_handler(commands=['list'])
async def tg_list_databases(message: types.Message):
    databases = list_databases(notion)

    answer = ''
    for database in databases:
        answer += f'{database.title}\n'
    await message.answer(answer)

# LOGIN

import logging
import os
from urllib.parse import urlencode

from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiohttp import web

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up Notion integration details
NOTION_CLIENT_ID = os.environ["NOTION_CLIENT_ID"]
NOTION_CLIENT_SECRET = os.environ["NOTION_CLIENT_SECRET"]
NOTION_REDIRECT_URI = os.environ["NOTION_REDIRECT_URI"]

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

# Start the bot
if __name__ == "__main__":
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
