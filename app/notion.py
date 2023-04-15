import os
from dataclasses import dataclass
from typing import NamedTuple

from dotenv import load_dotenv
from notion_client import Client as NotionCLI

load_dotenv()

token = os.environ.get('NOTION_KEY')
db_id = os.environ.get('NOTION_DB_ID')
notion = NotionCLI(auth=token)
bot_token = os.environ.get('BOT_TOKEN')


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
            try:
                title = block['title'][0]['plain_text']
            except KeyError:
                title = ""
            databases.append(
                Database(
                    id=block['id'],
                    title=title,
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
