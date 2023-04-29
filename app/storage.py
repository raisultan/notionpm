import json
from typing import Optional

from redis import asyncio as aioredis


class Storage:
    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def save_user_access_token(self, chat_id: str, access_token: str) -> None:
        await self._redis.set(f'access_token_{chat_id}', access_token)

    async def get_user_access_token(self, chat_id: str) -> Optional[str]:
        token = await self._redis.get(f'access_token_{chat_id}')
        if not token:
            return None
        return token.decode('utf-8')

    async def get_all_chat_ids(self) -> list:
        chat_ids = await self._redis.keys('access_token_*')
        if not chat_ids:
            return []
        return [chat_id.decode('utf-8').split('token_')[1] for chat_id in chat_ids]

    async def set_user_db_id(self, chat_id: str, db_id: str) -> None:
        await self._redis.set(f'db_id_{chat_id}', db_id)

    async def get_user_db_id(self, chat_id: str) -> Optional[str]:
        db_id = await self._redis.get(f'db_id_{chat_id}')
        if not db_id:
            return None
        return db_id.decode('utf-8')

    async def set_user_db_state(self, db_id: str, db_state: dict) -> None:
        await self._redis.set(f'db_state_{db_id}', json.dumps(db_state['results']))

    async def get_user_db_state(self, db_id: str) -> Optional[dict]:
        db_state = await self._redis.get(f'db_state_{db_id}')
        if not db_state:
            return None
        return json.loads(db_state)

    async def set_user_tracked_properties(self, chat_id: str, tracked_properties: list) -> None:
        await self._redis.set(f'tracked_properties_{chat_id}', json.dumps(tracked_properties))

    async def get_user_tracked_properties(self, chat_id: str) -> Optional[list]:
        tracked_properties = await self._redis.get(f'tracked_properties_{chat_id}')
        if not tracked_properties:
            return None
        return json.loads(tracked_properties)

    async def set_tracked_properties_message_id(self, chat_id: str, message_id: int) -> None:
        await self._redis.set(f'tracked_properties_message_id_{chat_id}', message_id)

    async def get_tracked_properties_message_id(self, chat_id: str) -> Optional[int]:
        message_id = await self._redis.get(f'tracked_properties_message_id_{chat_id}')
        if not message_id:
            return None
        return int(message_id)

    async def delete_tracked_properties_message_id(self, chat_id: str) -> None:
        await self._redis.delete(f'tracked_properties_message_id_{chat_id}')

    async def set_user_setup_status(self, chat_id: str, is_in_setup: bool) -> None:
        await self._redis.set(f'in_setup_{chat_id}', int(is_in_setup))

    async def get_user_setup_status(self, chat_id: str) -> bool:
        is_in_setup = await self._redis.get(f'in_setup_{chat_id}')
        if not is_in_setup:
            return False
        return bool(int(is_in_setup.decode('utf-8')))

    async def set_connect_message_id(self, chat_id: str, message_id: int) -> None:
        await self._redis.set(f'sent_connect_message_id_{chat_id}', message_id)

    async def get_connect_message_id(self, chat_id: str) -> Optional[int]:
        message_id = await self._redis.get(f'sent_connect_message_id_{chat_id}')
        if not message_id:
            return None
        return int(message_id.decode('utf-8'))

    async def set_user_notification_type(self, user_id: int, notification_type: str):
        key = f"user:{user_id}:notification_type"
        await self._redis.set(key, notification_type)

    async def set_user_notification_chat_id(self, user_id: int, chat_id: int):
        key = f"user:{user_id}:notification_chat_id"
        await self._redis.set(key, chat_id)

    async def get_user_notification_type(self, user_id: int) -> Optional[str]:
        key = f"user:{user_id}:notification_type"
        notification_type = await self._redis.get(key)
        if notification_type:
            return notification_type.decode('utf-8')
        return None

    async def get_user_notification_chat_id(self, user_id: int) -> Optional[int]:
        key = f"user:{user_id}:notification_chat_id"
        chat_id = await self._redis.get(key)
        if chat_id:
            return int(chat_id.decode('utf-8'))
        return None

    async def set_user_private_chat_id(self, user_id: int, chat_id: str) -> None:
        key = f"user:{user_id}:private_chat_id"
        await self._redis.set(key, chat_id)

    async def get_user_private_chat_id(self, user_id: int) -> Optional[int]:
        key = f"user:{user_id}:private_chat_id"
        chat_id = await self._redis.get(key)
        if chat_id:
            return int(chat_id.decode('utf-8'))
        return None
