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

########################################

NOTION_TOKEN = "secret_x2zo6k7taCVb7DFAQT4UauuHYh3DbMZdBjXETsivjUb"
notion = NotionCLI(NOTION_TOKEN)
NOTION_DB = os.environ["NOTION_DB_ID"]

from copy import deepcopy


def track_changes(old: list[dict], new: list[dict], props: list[str]):
    old, new = deepcopy(old), deepcopy(new)

    # get page id lists for old and new
    old_ids = [page['id'] for page in old]
    new_ids = [page['id'] for page in new]

    # get added and possibly changed pages from new list
    added_page_ids = [page_id for page_id in new_ids if page_id not in old_ids]
    print(f'Added: {added_page_ids}')
    added_pages = []
    new_for_tracking_props = []
    for page in new:
        if page['id'] in added_page_ids:
            added_pages.append(page)
        else:
            new_for_tracking_props.append(page)

    # get removed and possibly changed pages from old list
    removed_page_ids = [page_id for page_id in old_ids if page_id not in new_ids]
    print(f'Removed: {removed_page_ids}')
    removed_pages = []
    old_for_tracking_props = []
    for page in old:
        if page['id'] in removed_page_ids:
            removed_pages.append(page)
        else:
            old_for_tracking_props.append(page)

    # track changes in properties of new and old
    old_for_tracking_props = sorted(old_for_tracking_props, key=lambda page: page['id'])
    new_for_tracking_props = sorted(new_for_tracking_props, key=lambda page: page['id'])

    for old_page, new_page in zip(old_for_tracking_props, new_for_tracking_props):
        old_page_props = old_page['properties']
        new_page_props = new_page['properties']
        for prop in props:
            if old_page_props[prop] != new_page_props[prop]:
                print(
                    f'Property "{prop}" of page "{new_page_props["Name"]["title"][0]["plain_text"]}" '
                    f'changed from "{old_page_props[prop]}" to "{new_page_props[prop]}"'
                )
