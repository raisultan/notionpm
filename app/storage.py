import json
from typing import Optional

from redis import asyncio as aioredis

redis = aioredis.from_url("redis://localhost")


async def save_user_access_token(chat_id: str, access_token: str) -> None:
    await redis.set(f'chat_{chat_id}', access_token)


async def get_user_access_token(chat_id: str) -> Optional[str]:
    token = await redis.get(f'chat_{chat_id}')
    if not token:
        return None
    return json.loads(token)


async def get_all_chat_ids() -> list:
    chat_ids = await redis.keys('chat_*')
    if not chat_ids:
        return []
    return json.loads(chat_ids)


async def set_user_db_id(chat_id: str, db_id: str) -> None:
    await redis.set(f'db_{chat_id}', db_id)


async def get_user_db_id(chat_id: str) -> Optional[str]:
    db_id = await redis.get(f'db_{chat_id}')
    if not db_id:
        return None
    return json.loads(db_id)


async def set_user_db_state(db_id: str, db_state: dict) -> None:
    await redis.set(f'db_state_{db_id}', db_state)


async def get_user_db_state(db_id: str) -> Optional[dict]:
    db_state = await redis.get(f'db_state_{db_id}')
    if not db_state:
        return None
    return json.loads(db_state)


async def set_user_tracked_properties(chat_id: str, tracked_properties: list) -> None:
    await redis.set(f'tracked_properties_{chat_id}', tracked_properties)


async def get_user_tracked_properties(chat_id: str) -> Optional[list]:
    tracked_properties = await redis.get(f'tracked_properties_{chat_id}')
    if not tracked_properties:
        return None
    return json.loads(tracked_properties)
