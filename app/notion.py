from dataclasses import dataclass

from notion_client import Client as NotionCLI


@dataclass(frozen=True)
class Database:
    id: str
    title: str


@dataclass
class Page:
    id: str
    title: str
    properties: dict


class NotionClient(NotionCLI):
    def list_databases(self) -> list[Database]:
        blocks = self.search()
        databases = []

        for block in blocks['results']:
            if block['object'] == 'database':
                try:
                    title = block['title'][0]['plain_text']
                except (KeyError, IndexError):
                    title = "Couldn't get the title 🎅"
                databases.append(
                    Database(
                        id=block['id'],
                        title=title,
                    ),
                )

        return databases

    def list_pages_from(self, db_id: str) -> list[Page]:
        blocks = self.databases.query(db_id)
        pages = []

        for block in blocks['results']:
            pages.append(
                Page(
                    id=block['id'],
                    title=block['Name']['title'][0]['plain_text'],
                    properties=block['properties'],
                )
            )
        return pages
