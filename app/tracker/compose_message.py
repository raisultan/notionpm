from datetime import datetime
from typing import Any, Optional
from html import escape

from aiogram.types import ParseMode

from app.tracker.entities import Page, PageChange, Property


def to_user_friendly_dt(date_string: Optional[str]) -> str:
    if not date_string:
        return ''

    if len(date_string) > 10:
        dt = datetime.fromisoformat(date_string)
        date_string = dt.strftime("%Y-%m-%d %l:%M%p").replace(":00", "").strip()
    return date_string


def compose_property_diff(old: Property, new: Property) -> tuple[str, str, str]:
    if old.type == 'title':
        emoji = '🔎'
        old_value = old.content[0]['plain_text']
        new_value = new.content[0]['plain_text']
    elif old.type == 'status':
        emoji = '🚦'
        old_value = old.content['name']
        new_value = new.content['name']
    elif old.type == 'select':
        emoji = '🚦'
        old_value = old.content['name']
        new_value = new.content['name']
    elif old.type == 'date':
        emoji = '📅'
        old_start = to_user_friendly_dt(old.content['start'] if old.content else None)
        new_start = to_user_friendly_dt(new.content['start'] if new.content else None)
        old_end = to_user_friendly_dt(old.content['end'] if old.content else None)
        new_end = to_user_friendly_dt(new.content['end'] if new.content else None)
        # old value
        if old_start and not old_end:
            old_value = old_start
        else:
            old_value = f'{old_start} to {old_end}'
        # new value
        if new_start and not new_end:
            new_value = new_start
        else:
            new_value = f'{new_start} to {new_end}'
    elif old.type == 'people':
        emoji = '🦹‍♀️'
        old_value = ', '.join([person['name'] for person in old.content])
        new_value = ', '.join([person['name'] for person in new.content])
    elif old.type == 'url':
        emoji = '🔗'
        old_value = old.content
        new_value = new.content
    else:
        emoji = '🤷‍♀️'
        old_value, new_value = 'unknown', 'unknown'
    return emoji, old_value, new_value


def escape_html(any: Any) -> str:
    return escape(str(any))


def compose_page_change(page_change: PageChange) -> tuple[str, str]:
    messages = []
    for field_change in page_change.field_changes:
        field_message = (
            f"{field_change.emoji} <b>{escape_html(field_change.name)}</b>: "
            f"{escape_html(field_change.old_value)} → "
            f"{escape_html(field_change.new_value)}\n\n"
        )
        messages.append(field_message)

    message = (
        f"📬 Changes in <a href='{escape_html(page_change.url)}'>"
        f"{escape_html(page_change.name)}</a>:\n\n"
        f"{''.join(messages)}"
    )
    return message, ParseMode.HTML


def compose_page_added(page: Page) -> tuple[str, str]:
    text = f"🌱 New page added: <a href='{escape_html(page.url)}'>{escape_html(page.name)}</a>"
    return text, ParseMode.HTML


def compose_page_removed(page: Page) -> tuple[str, str]:
    text = f"🗑️ Page removed: <a href='{escape_html(page.url)}'>{escape_html(page.name)}</a>"
    return text, ParseMode.HTML
