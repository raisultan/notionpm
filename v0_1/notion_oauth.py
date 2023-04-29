import base64
from typing import Any, Optional

import aiohttp
from aiohttp.web_request import Request
from notion_client import Client as NotionCLI


class NotionOAuth:
    def __init__(
        self,
        storage: Any,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        self.storage = storage
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    async def make_oauth_request(self, code: str) -> dict:
        auth_creds = f"{self.client_id}:{self.client_secret}"
        encoded_auth_creds = base64.b64encode(auth_creds.encode("ascii")).decode("ascii")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_auth_creds}",
        }
        json = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        async with aiohttp.ClientSession() as http_client:
            response = await http_client.post(
                "https://api.notion.com/v1/oauth/token",
                json=json,
                headers=headers,
            )
            response_json = await response.json()
            await response.release()
        return response_json

    async def handle_oauth(self, request: Request) -> Optional[str]:
        """
        :return: chat_id of the user who authorized the bot
        """
        try:
            code = request.query["code"]
            state = request.query["state"]
            chat_id = state.split("-")[1]

            response = await self.make_oauth_request(code)
            access_token = response["access_token"]

            NotionCLI(auth=access_token).search()
            await self.storage.save_user_access_token(chat_id, access_token)
        except Exception as exc:
            print('Error while handling oauth:', repr(exc))
            chat_id = None
        return chat_id

    def generate_connect_url(self, chat_id: str) -> str:
        return (
            "https://api.notion.com/v1/oauth/authorize"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&state=instance-{chat_id}"
        )
