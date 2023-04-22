import json
from typing import Optional

from redis import asyncio as aioredis

redis = aioredis.from_url("redis://localhost")


async def save_user_access_token(chat_id: str, access_token: str) -> None:
    await redis.set(f'access_token_{chat_id}', access_token)


async def get_user_access_token(chat_id: str) -> Optional[str]:
    token = await redis.get(f'access_token_{chat_id}')
    if not token:
        return None
    return token.decode('utf-8')


async def get_all_chat_ids() -> list:
    chat_ids = await redis.keys('access_token_*')
    if not chat_ids:
        return []
    return [chat_id.decode('utf-8').split('token_')[1] for chat_id in chat_ids]


async def set_user_db_id(chat_id: str, db_id: str) -> None:
    await redis.set(f'db_id_{chat_id}', db_id)


async def get_user_db_id(chat_id: str) -> Optional[str]:
    db_id = await redis.get(f'db_id_{chat_id}')
    if not db_id:
        return None
    return db_id.decode('utf-8')


async def set_user_db_state(db_id: str, db_state: dict) -> None:
    await redis.set(f'db_state_{db_id}', json.dumps(db_state['results']))


async def get_user_db_state(db_id: str) -> Optional[dict]:
    db_state = await redis.get(f'db_state_{db_id}')
    if not db_state:
        return None
    return json.loads(db_state)


async def set_user_tracked_properties(chat_id: str, tracked_properties: list) -> None:
    await redis.set(f'tracked_properties_{chat_id}', json.dumps(tracked_properties))


async def get_user_tracked_properties(chat_id: str) -> Optional[list]:
    tracked_properties = await redis.get(f'tracked_properties_{chat_id}')
    if not tracked_properties:
        return None
    return json.loads(tracked_properties)


async def set_tracked_properties_message_id(chat_id: str, message_id: int) -> None:
    await redis.set(f'tracked_properties_message_id_{chat_id}', message_id)


async def get_tracked_properties_message_id(chat_id: str) -> Optional[int]:
    message_id = await redis.get(f'tracked_properties_message_id_{chat_id}')
    if not message_id:
        return None
    return int(message_id)


async def delete_tracked_properties_message_id(chat_id: str) -> None:
    await redis.delete(f'tracked_properties_message_id_{chat_id}')


async def set_user_setup_status(chat_id: str, is_in_setup: bool) -> None:
    await redis.set(f'in_setup_{chat_id}', int(is_in_setup))


async def get_user_setup_status(chat_id: str) -> bool:
    is_in_setup = await redis.get(f'in_setup_{chat_id}')
    if not is_in_setup:
        return False
    return bool(int(is_in_setup.decode('utf-8')))
