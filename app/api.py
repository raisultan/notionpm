import os
import requests, json

from dotenv import load_dotenv

load_dotenv()

token = os.environ.get('NOTION_KEY')
db_id = os.environ.get('NOTION_DB_ID')
headers = {
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "Notion-Version": "2022-02-22"
}


def get_db(db_id: str, headers: dict) -> dict:
    url = f"https://api.notion.com/v1/databases/{db_id}"
    response = requests.request("GET", url, headers=headers)
    return response.json()


def list_pages_in_db(db_id: str, headers: dict) -> dict:
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    response = requests.request("POST", url, headers=headers)
    return response.json()


def get_page(page_id: str, headers: dict) -> dict:
    url = f"https://api.notion.com/v1/pages/{page_id}"
    response = requests.request("GET", url, headers=headers)
    return response.json()


def get_block_children(block_id: str, headers: dict, page_size: int = 100) -> dict:
    # page is block too, so you can content of the page using this
    url = f"https://api.notion.com/v1/blocks/{block_id}/children?page_size={page_size}"
    response = requests.request("GET", url, headers=headers)
    return response.json()


def get_block(block_id: str, headers: dict) -> dict:
    url = f"https://api.notion.com/v1/blocks/{block_id}"
    response = requests.request("GET", url, headers=headers)
    return response.json()


def create_page(db_id: str, headers: dict) -> int:
    url = 'https://api.notion.com/v1/pages'
    data = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {"title": [{"text": {"content": "DONA"}}]},
            "Text": {
                "rich_text": [
                    {
                        "text": {"content": "This is thienqc"},
                    }
                ]
            },
            "Checkbox": {"checkbox": True},
            "Number": {"number": 1999},
            "Select": {
                "select": {
                    "name": "Mouse",
                }
            },
            "Multi-select": {
                "multi_select": [
                    {
                        "name": "Apple",
                    },
                    {
                        "name": "Banana",
                    },
                ]
            },
            "Date": {
                "date": {
                    "start": "2022-08-05",
                    "end": "2022-08-10",
                }
            },
            "URL": {"url": "google.com"},
            "Email": {"email": "dolor@ipsum.com"},
            "Phone": {"phone_number": "19191919"},
            "Person": {
                "people": [
                    {
                        "id": "4af42d2d-a077-4808-b4f7-e960a93fd945",
                    }
                ]
            },
            "Relation": {"relation": [{"id": "fbb0a7f2-413e-4728-adbf-281ab14f0c33"}]},
        },
    }
    response = requests.request(
        "POST",
        url,
        headers=headers,
        data=json.dumps(data),
    )
    return response.status_code


def update_page(page_id: str, headers: dict) -> int:
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "Name": {"title": [{"text": {"content": "THIENQCCCCCC"}}]},
            "Text": {
                "rich_text": [
                    {
                        "text": {"content": "My name is Thienqc"},
                    }
                ]
            },
            "Checkbox": {"checkbox": False},
            "Number": {"number": 2004},
            "Select": {
                "select": {
                    "name": "Mickey",
                }
            },
            "Multi-select": {
                "multi_select": [
                    {
                        "name": "Coconut",
                    },
                    {
                        "name": "Banana",
                    },
                ]
            },
            "Date": {
                "date": {
                    "start": "2022-08-04",
                    "end": "2022-08-09",
                }
            },
            "URL": {"url": "ipsum.com"},
            "Email": {"email": "thienqc@ipsum.com"},
            "Phone": {"phone_number": "32323232"},
            "Person": {
                "people": [
                    {
                        "id": "4af42d2d-a077-4808-b4f7-e960a93fd945",
                    }
                ]
            },
            "Relation": {"relation": [{"id": "6c320979581b44819d84f941f7eddc41"}]},
        }
    }
    response = requests.request(
        "PATCH",
        url,
        headers=headers,
        data=json.dumps(data),
    )
    return response.status_code
