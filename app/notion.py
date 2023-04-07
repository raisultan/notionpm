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
from typing import Any


@dataclass
class PropertyChange:
    name: str
    old_value: Any
    new_value: Any


@dataclass
class PageChange:
    name: str
    url: str
    field_changes: list[PropertyChange]


def track_db_changes(old: list[dict], new: list[dict], props: list[str]) -> list[PageChange]:
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

    db_changes = []
    for old_page, new_page in zip(old_for_tracking_props, new_for_tracking_props):
        old_page_props = old_page['properties']
        new_page_props = new_page['properties']
        page_property_changes = []
        for prop in props:
            if old_page_props[prop] != new_page_props[prop]:
                old_value, new_value = track_change_on_property(old_page_props[prop], new_page_props[prop])
                page_property_changes.append(PropertyChange(prop, old_value, new_value))
        if page_property_changes:
            db_changes.append(
                PageChange(
                    get_page_name(old_page),
                    get_page_url(old_page),
                    page_property_changes,
                )
            )
    return db_changes


def track_change_on_property(old: dict, new: dict) -> tuple:
    if old['type'] == 'title':
        old = old['title'][0]['plain_text']
        new = new['title'][0]['plain_text']
        return old, new
    elif old['type'] == 'status':
        old = old['status']['name']
        new = new['status']['name']
        return old, new
    elif old['type'] == 'date':
        old_start = old['date']['start']
        new_start = new['date']['start']
        old_end = old['date']['end']
        new_end = new['date']['end']
        return f'{old_start} -> {old_end}', f'{new_start} -> {new_end}'
    elif old['type'] == 'people':
        old = [person['name'] for person in old['people']]
        new = [person['name'] for person in new['people']]
        return old, new
    elif old['type'] == 'url':
        old = old['url']
        new = new['url']
        return old, new
    else:
        return 'unknown', 'unknown'


def get_page_name(page: dict) -> str:
    return page['properties']['Name']['title'][0]['plain_text']

def get_page_url(page: dict) -> str:
    return page['url']
