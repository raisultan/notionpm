from __future__ import annotations
import logging
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Union
from html import escape

from aiogram.types import ParseMode
from aiohttp.web import Application

from app.notion import NotionClient

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


@dataclass
class PropertyChange:
    name: str
    old_value: str
    new_value: str
    emoji: str


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
            try:
                if old_page_props[prop] != new_page_props[prop]:
                    emoji, old_value, new_value = track_change_on_property(
                        old_page_props[prop],
                        new_page_props[prop],
                    )
                    page_property_changes.append(PropertyChange(prop, old_value, new_value, emoji))
            except Exception as ex:
                logger.error(f'Error while tracking changes in property {prop}: {ex}')
                continue
        if page_property_changes:
            db_changes.append(
                PageChange(
                    get_page_name(old_page),
                    get_page_url(old_page),
                    page_property_changes,
                )
            )
    return db_changes, added_pages, removed_pages


def track_change_on_property(old: dict, new: dict) -> tuple:
    if old['type'] == 'title':
        emoji = '🔎'
        old = old['title'][0]['plain_text']
        new = new['title'][0]['plain_text']
    elif old['type'] == 'status':
        emoji = '🚦'
        old = old['status']['name']
        new = new['status']['name']
    elif old['type'] == 'select':
        emoji = '🚦'
        old = old['select']['name']
        new = new['select']['name']
    elif old['type'] == 'date':
        emoji = '📅'
        old_start = to_user_friendly_dt(old['date']['start'] if old['date'] else None)
        new_start = to_user_friendly_dt(new['date']['start'] if new['date'] else None)
        old_end = to_user_friendly_dt(old['date']['end'] if old['date'] else None)
        new_end = to_user_friendly_dt(new['date']['end'] if new['date'] else None)
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
    elif old['type'] == 'people':
        emoji = '🦹‍♀️'
        old = ', '.join([person['name'] for person in old['people']])
        new = ', '.join([person['name'] for person in new['people']])
    elif old['type'] == 'url':
        emoji = '🔗'
        old = old['url']
        new = new['url']
        return old, new
    else:
        emoji = '🤷‍♀️'
        old, new = 'unknown', 'unknown'
    return emoji, old, new

def get_page_name(page: dict) -> str:
    title_prop = page['properties']['Name']['title']
    if title_prop:
        return title_prop[0]['plain_text']
    else:
        return 'Untitled'


def get_page_url(page: dict) -> str:
    return page['url']


def escape_html(any: Any) -> str:
    return escape(str(any))


def create_properties_changed_message(page_change: PageChange) -> tuple:
    messages = []
    for field_change in page_change.field_changes:
        field_message = (
            f"{field_change.emoji} <b>{escape_html(field_change.name)}</b>: "
            f"{escape_html(str(field_change.old_value))} → "
            f"{escape_html(str(field_change.new_value))}\n\n"
        )
        messages.append(field_message)

    message = (
        f"📬 Changes in <a href='{escape_html(page_change.url)}'>{escape_html(page_change.name)}</a>:\n\n"
        f"{''.join(messages)}"
    )
    return message


async def track_changes_for_all(app: Application):
    storage = app['storage']
    bot = app['bot']

    logger.info('Tracking changes for all users...')
    active_notification_chat_ids = await storage.get_all_active_notification_chat_ids()
    if not active_notification_chat_ids:
        logger.warning('No chat ids found!')
        return

    for user_chat_id in active_notification_chat_ids:
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
            continue

        try:
            notion = NotionClient(auth=access_token)
            old_db_state = await storage.get_user_db_state(db_id)
            new_db_state = notion.databases.query(database_id=db_id)
            changes, added_pages, removed_pages = track_db_changes(
                old_db_state,
                new_db_state['results'],
                track_props,
            )
            await storage.set_user_db_state(db_id, new_db_state)
        except Exception as e:
            logger.exception(f'Exception for {chat_id}: {repr(e)}')
            continue

        for page in added_pages:
            page_name = get_page_name(page)
            page_url = get_page_url(page)
            added_message = f"🌱 New page added: <a href='{escape_html(page_url)}'>{escape_html(page_name)}</a>"
            await bot.send_message(chat_id, added_message, parse_mode=ParseMode.HTML)

        for page in removed_pages:
            page_name = get_page_name(page)
            page_url = get_page_url(page)
            removed_message = f"🗑️ Page removed: <a href='{escape_html(page_url)}'>{escape_html(page_name)}</a>"
            await bot.send_message(chat_id, removed_message, parse_mode=ParseMode.HTML)

        # Send messages for changes
        for page_change in changes:
            change_message = create_properties_changed_message(page_change)
            await bot.send_message(
                chat_id,
                change_message,
                parse_mode=ParseMode.HTML,
            )

        logger.info(f'Changes for {chat_id}: {changes}')
    logger.info('Done!')


"""
Entities:
- Page
    - id
    - created_time
    - last_edited_time
    - created_by
    - last_edited_by
    - cover
    - icon
    - parent
    - archived
    - url
    - properties
- Property
    - id
    - type
    - content
"""

"""
[
    {
        "object": "page",
        "id": "d9aecf28-2a7e-48d8-adc8-e474a9e7c761",
        "created_time": "2023-05-10T16:55:00.000Z",
        "last_edited_time": "2023-05-12T20:04:00.000Z",
        "created_by": {"object": "user", "id": "346a04af-8943-4e0d-940d-3fd186020991"},
        "last_edited_by": {
            "object": "user",
            "id": "346a04af-8943-4e0d-940d-3fd186020991",
        },
        "cover": None,
        "icon": None,
        "parent": {
            "type": "database_id",
            "database_id": "2678441b-ed57-4ac5-8c33-bdf33650b6c1",
        },
        "archived": False,
        "properties": {
            "Assign": {
                "id": "HsYh",
                "type": "people",
                "people": [
                    {
                        "object": "user",
                        "id": "346a04af-8943-4e0d-940d-3fd186020991",
                        "name": "raisultan",
                        "avatar_url": "https://s3-us-west-2.amazonaws.com/public.notion-static.com/2c4ed0ff-1a60-413d-b32e-0f08288cf854/Screenshot_2021-06-18_at_13.41.45.png",
                        "type": "person",
                        "person": {"email": "raisultan@proton.me"},
                    },
                    {
                        "object": "user",
                        "id": "bd83f89f-62c0-4193-b9ae-ed2ff84eaaec",
                        "name": "Alex",
                        "avatar_url": "https://s3-us-west-2.amazonaws.com/public.notion-static.com/2fa16287-9705-4ef0-82fa-050be2ec859c/_-1.jpg",
                        "type": "person",
                        "person": {"email": "oklimova-ki18@stud.sfu-kras.ru"},
                    },
                ],
            },
            "Email": {"id": "NVsM", "type": "email", "email": None},
            "Due date": {
                "id": "PJ%5D%3C",
                "type": "date",
                "date": {
                    "start": "2023-05-08T14:00:00.000+02:00",
                    "end": "2023-05-27T23:00:00.000+02:00",
                    "time_zone": None,
                },
            },
            "Status": {
                "id": "XdYK",
                "type": "status",
                "status": {
                    "id": "57fefebb-e836-4b0f-b964-80a3a8ddba08",
                    "name": "Done",
                    "color": "green",
                },
            },
            "some url": {"id": "Yir%3C", "type": "url", "url": None},
            "Related Notion Bot Test": {
                "id": "ZsHE",
                "type": "relation",
                "relation": [],
                "has_more": False,
            },
            "Name": {
                "id": "title",
                "type": "title",
                "title": [
                    {
                        "type": "text",
                        "text": {"content": "New task in complete", "link": None},
                        "annotations": {
                            "bold": False,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                            "code": False,
                            "color": "default",
                        },
                        "plain_text": "New task in complete",
                        "href": None,
                    }
                ],
            },
        },
        "url": "https://www.notion.so/New-task-in-complete-d9aecf282a7e48d8adc8e474a9e7c761",
    },
]
"""


@dataclass(frozen=True)
class Property:
    id: str
    type: str
    content: Optional[Union[list, dict]]

    @classmethod
    def from_json(cls, json: dict) -> 'Property':
        return cls(
            id=json['id'],
            type=json['type'],
            content=json[json['type']],
        )

@dataclass(frozen=True)
class Page:
    id: str
    created_time: str
    last_edited_time: str
    created_by: dict
    last_edited_by: dict
    cover: Optional[dict]
    icon: Optional[dict]
    parent: Optional[dict]
    archived: bool
    url: str
    properties: list[Property]

    @property
    def name(self) -> str:
        for property in self.properties:
            if property.type == 'title' and property.content:
                return property.content[0]['plain_text']
        return 'Unnamed page 🤷‍♀️'

    @classmethod
    def from_json(cls, json: dict) -> 'Page':
        properties = [Property.from_json(property) for property in json['properties']]
        return cls(
            id=json['id'],
            created_time=json['created_time'],
            last_edited_time=json['last_edited_time'],
            created_by=json['created_by'],
            last_edited_by=json['last_edited_by'],
            cover=json['cover'],
            icon=json['icon'],
            parent=json['parent'],
            archived=json['archived'],
            url=json['url'],
            properties=properties,
        )
