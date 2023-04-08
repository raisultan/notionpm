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
