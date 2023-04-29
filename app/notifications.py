import logging
import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from html import escape

from aiogram import Bot
from aiogram.types import ParseMode
from dotenv import load_dotenv
from notion_client import Client as NotionCLI
from rocketry import Rocketry
from rocketry.conds import every

from app.dispatcher import storage

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(token=os.environ["BOT_TOKEN"])


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
    if not old:
        old = []

    # get page id lists for old and new
    old_ids = [page['id'] for page in old] if old else []
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
        old_start = old['date']['start'] if old['date'] else None
        new_start = new['date']['start'] if new['date'] else None
        old_end = old['date']['end'] if old['date'] else None
        new_end = new['date']['end'] if new['date'] else None
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


def escape_html(any: Any) -> str:
    return escape(str(any))


def create_properties_changed_message_with_button(page_change: PageChange) -> tuple:
    messages = []
    for field_change in page_change.field_changes:
        field_message = (
            f"<b>{escape_html(field_change.name)}</b>: "
            f"{escape_html(str(field_change.old_value))} → "
            f"{escape_html(str(field_change.new_value))}\n\n"
        )
        messages.append(field_message)

    message = (
        f"📄 Changes in <a href='{escape_html(page_change.url)}'>{escape_html(page_change.name)}</a>:\n\n"
        f"{''.join(messages)}"
    )

    return message


app = Rocketry()

@app.task(every('10 seconds'))
async def track_changes_for_all():
    logger.info('Tracking changes for all users...')
    chat_ids = await storage.get_all_chat_ids()
    if not chat_ids:
        logger.warning('No chat ids found!')
        return

    for chat_id in chat_ids:
        access_token = await storage.get_user_access_token(chat_id)
        db_id = await storage.get_user_db_id(chat_id)
        track_props = await storage.get_user_tracked_properties(chat_id)

        if not access_token or not db_id or not track_props:
            logger.warning(f'Setup not completed for {chat_id}! Skipping...')
            continue

        try:
            notion = NotionCLI(auth=access_token)
            old_db_state = await storage.get_user_db_state(db_id)
            new_db_state = notion.databases.query(database_id=db_id)
            changes = track_db_changes(old_db_state, new_db_state['results'], track_props)
            await storage.set_user_db_state(db_id, new_db_state)
        except Exception as e:
            logger.exception(f'Exception for {chat_id}: {repr(e)}')
            continue
        if not changes:
            logger.info(f'No changes for {chat_id} - {db_id}!')
            continue

        for page_change in changes:
            change_message = create_properties_changed_message_with_button(page_change)
            await bot.send_message(
                chat_id,
                change_message,
                parse_mode=ParseMode.HTML,
            )

        logger.info(f'Changes for {chat_id}: {changes}')
    logger.info('Done!')
