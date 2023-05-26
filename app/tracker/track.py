from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from typing import Any, Optional
from html import escape

from aiogram.types import ParseMode
from aiohttp.web import Application

from app.notion import NotionClient
from app.tracker.entities import Page, PageChange, Property, PropertyChange

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def to_user_friendly_dt(date_string: Optional[str]) -> str:
    if not date_string:
        return ''

    if len(date_string) > 10:
        dt = datetime.fromisoformat(date_string)
        date_string = dt.strftime("%Y-%m-%d %l:%M%p").replace(":00", "").strip()
    return date_string


def track_db_changes(old: list[Page], new: list[Page], tracked_properties: list[str]):
    # get page id lists for old and new
    old_ids = [page.id for page in old] if old else []
    new_ids = [page.id for page in new]

    # get added and possibly changed pages from new list
    added_page_ids = [page_id for page_id in new_ids if page_id not in old_ids]
    logger.info(f'Added: {added_page_ids}')
    added_pages = []
    changed_pages_from_new = []
    for page in new:
        if page.id in added_page_ids:
            added_pages.append(page)
        else:
            changed_pages_from_new.append(page)

    # get removed and possibly changed pages from old list
    removed_page_ids = [page_id for page_id in old_ids if page_id not in new_ids]
    logger.info(f'Removed: {removed_page_ids}')
    removed_pages = []
    changed_pages_from_old = []
    for page in old:
        if page.id in removed_page_ids:
            removed_pages.append(page)
        else:
            changed_pages_from_old.append(page)

    # track changes in properties of new and old
    sorted_old = sorted(changed_pages_from_old, key=lambda page: page.id)
    sorted_new = sorted(changed_pages_from_new, key=lambda page: page.id)

    db_changes = []
    for old_page, new_page in zip(sorted_old, sorted_new):
        old_page_props = [property for property in old_page.properties if property.name in tracked_properties]
        new_page_props = [property for property in new_page.properties if property.name in tracked_properties]
        page_property_changes = []
        for old_property, new_property in zip(old_page_props, new_page_props):
            try:
                if old_property.content != new_property.content:
                    emoji, old_value, new_value = track_change_on_property(old_property, new_property)
                    page_property_changes.append(PropertyChange(old_property.name, old_value, new_value, emoji))
            except Exception as ex:
                logger.error(f'Error while tracking changes in property {old_property.name}: {ex}')
                continue

        if page_property_changes:
            db_changes.append(
                PageChange(
                    old_page.name,
                    old_page.url,
                    page_property_changes,
                )
            )
    return db_changes, added_pages, removed_pages


def track_change_on_property(old: Property, new: Property) -> tuple:
    if old.type == 'title':
        emoji = '🔎'
        old = old.content[0]['plain_text']
        new = new.content[0]['plain_text']
    elif old.type == 'status':
        emoji = '🚦'
        old = old.content['name']
        new = new.content['name']
    elif old.type == 'select':
        emoji = '🚦'
        old = old.content['name']
        new = new.content['name']
    elif old.type == 'date':
        emoji = '📅'
        old_start = to_user_friendly_dt(old.content['start'] if old.content else None)
        new_start = to_user_friendly_dt(new.content['start'] if new.content else None)
        old_end = to_user_friendly_dt(old.content['end'] if old.content else None)
        new_end = to_user_friendly_dt(new.content['end'] if new.content else None)
        # old value
        if old_start and not old_end:
            old = old_start
        else:
            old = f'{old_start} to {old_end}'
        # new value
        if new_start and not new_end:
            new = new_start
        else:
            new = f'{new_start} to {new_end}'
    elif old.type == 'people':
        emoji = '🦹‍♀️'
        old = ', '.join([person['name'] for person in old.content])
        new = ', '.join([person['name'] for person in new.content])
    elif old.type == 'url':
        emoji = '🔗'
        old = old.content
        new = new.content
    else:
        emoji = '🤷‍♀️'
        old, new = 'unknown', 'unknown'
    return emoji, old, new


def escape_html(any: Any) -> str:
    return escape(str(any))


def create_properties_changed_message(page_change: PageChange) -> str:
    messages = []
    for field_change in page_change.field_changes:
        field_message = (
            f"{field_change.emoji} <b>{escape_html(field_change.name)}</b>: "
            f"{escape_html(field_change.old_value)} → "
            f"{escape_html(field_change.new_value)}\n\n"
        )
        messages.append(field_message)

    message = (
        f"📬 Changes in <a href='{escape_html(page_change.url)}'>{escape_html(page_change.name)}</a>:\n\n"
        f"{''.join(messages)}"
    )
    return message

async def track_changes(app: Application, user_chat_id: int):
    storage = app['storage']
    bot = app['bot']

    chat_id = await storage.get_user_notification_chat_id(user_chat_id)
    if not chat_id:
        logger.warning(
            f'No notification chat id found for {user_chat_id}! Skipping...'
        )

    access_token = await storage.get_user_access_token(user_chat_id)
    db_id = await storage.get_user_db_id(user_chat_id)
    track_props = await storage.get_user_tracked_properties(user_chat_id)

    if not access_token or not db_id or not track_props:
        logger.warning(f'Setup not completed for {user_chat_id}! Skipping...')
        return

    notion = NotionClient(auth=access_token)
    old_db_state = await storage.get_user_db_state(db_id)
    new_db_state = notion.databases.query(database_id=db_id)
    old = [Page.from_json(page) for page in old_db_state]
    new = [Page.from_json(page) for page in new_db_state['results']]
    changes, added_pages, removed_pages = track_db_changes(
        old,
        new,
        track_props,
    )
    await storage.set_user_db_state(db_id, new_db_state)

    for page in added_pages:
        added_message = f"🌱 New page added: <a href='{escape_html(page.url)}'>{escape_html(page.name)}</a>"
        await bot.send_message(chat_id, added_message, parse_mode=ParseMode.HTML)

    for page in removed_pages:
        removed_message = f"🗑️ Page removed: <a href='{escape_html(page.url)}'>{escape_html(page.name)}</a>"
        await bot.send_message(chat_id, removed_message, parse_mode=ParseMode.HTML)

    for page_change in changes:
        change_message = create_properties_changed_message(page_change)
        await bot.send_message(
            chat_id,
            change_message,
            parse_mode=ParseMode.HTML,
        )
    logger.info(f'Changes for {chat_id}: {changes}')


async def track_changes_for_all(app: Application):
    storage = app['storage']

    logger.info('Tracking changes for all users...')
    active_notification_chat_ids = await storage.get_all_active_notification_chat_ids()
    if not active_notification_chat_ids:
        logger.warning('No chat ids found!')
        return

    tasks = [track_changes(app, user_chat_id) for user_chat_id in active_notification_chat_ids]
    asyncio.gather(*tasks)
