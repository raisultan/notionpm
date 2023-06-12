import asyncio
import logging

from aiohttp.web import Application
from httpx import ReadTimeout
from notion_client.errors import APIResponseError

from app.notion import NotionClient
from app.tracker.entities import Page, PageChange, PropertyChange
from app.tracker.compose_message import (
    compose_page_added,
    compose_page_change,
    compose_page_removed,
    compose_property_diff,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
                    emoji, old_value, new_value = compose_property_diff(old_property, new_property)
                    page_property_changes.append(PropertyChange(old_property.name, old_value, new_value, emoji))
            except Exception as ex:
                logger.error(
                    f'Error while tracking changes in property {old_property.name}: {repr(ex)}'
                )
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
    try:
        new_db_state = notion.databases.query(database_id=db_id)
    except APIResponseError as e:
        logger.error(f'Error while querying database {db_id}: {repr(e)}')
        await storage.remove_user_db_id(user_chat_id)
        await bot.send_message(
            "Oops, we haven't found your database in Notion 😢\n"
            "Did you do something with it!?\n\n"
            "Try to reconnect your workspace with /connect command 🥺",
            user_chat_id,
        )
        return
    except ReadTimeout as e:
        logger.error(f'Took too long to track changes for {db_id}: {repr(e)}')
        return

    old = [Page.from_json(page) for page in old_db_state]
    new = [Page.from_json(page) for page in new_db_state['results']]
    changes, added_pages, removed_pages = track_db_changes(old, new, track_props)
    await storage.set_user_db_state(db_id, new_db_state)

    for page in added_pages:
        added_message, parse_mode = compose_page_added(page)
        await bot.send_message(chat_id, added_message, parse_mode=parse_mode)

    for page in removed_pages:
        removed_message, parse_mode = compose_page_removed(page)
        await bot.send_message(chat_id, removed_message, parse_mode=parse_mode)

    for page_change in changes:
        change_message, parse_mode = compose_page_change(page_change)
        await bot.send_message(chat_id, change_message, parse_mode=parse_mode)
    logger.info(f'Changes for {chat_id}: {changes}')


async def track_changes_for_all(app: Application):
    storage = app['storage']

    logger.info('Tracking changes for all users...')
    active_notification_chat_ids = await storage.get_all_active_notification_chat_ids()
    if not active_notification_chat_ids:
        logger.warning('No chat ids found!')
        return

    tasks = []
    for user_chat_id in active_notification_chat_ids:
        tasks.append(asyncio.create_task(track_changes(app, user_chat_id)))
    asyncio.gather(*tasks)
