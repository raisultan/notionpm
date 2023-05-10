import os

from dotenv import load_dotenv

load_dotenv()


def load_config() -> dict:
    return {
        'notion_client_id': os.environ["NOTION_CLIENT_ID"],
        'notion_client_secret': os.environ["NOTION_CLIENT_SECRET"],
        'notion_redirect_uri': os.environ["NOTION_REDIRECT_URI"],
        'bot_url': os.environ["BOT_URL"],
        'bot_token': os.environ["BOT_TOKEN"],
    }
