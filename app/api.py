import os

from typing import NamedTuple
from dataclasses import dataclass

from dotenv import load_dotenv
from notion_client import Client as NotionCLI
from aiogram import Bot, Dispatcher, executor, types

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


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
