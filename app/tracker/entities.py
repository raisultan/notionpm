from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional, Union


@dataclass(frozen=True)
class Property:
    id: str
    name: str
    type: str
    content: Optional[Union[list, dict]]

    @classmethod
    def from_json(cls, name: str, json: dict) -> 'Property':
        return cls(
            id=json['id'],
            name=name,
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
        properties = []
        for name, content in json['properties'].items():
            properties.append(Property.from_json(name, content))

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


@dataclass(frozen=True)
class PropertyChange:
    name: str
    old_value: str
    new_value: str
    emoji: str


@dataclass(frozen=True)
class PageChange:
    name: str
    url: str
    field_changes: list[PropertyChange]
