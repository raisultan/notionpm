## NotionPM

NotionPM (Notion Project Management) is a tool that helps teams using Notion for Project Management
and Telegram for communcation to be more effective and stay up-to-date with any changes related to 
projects.

It monitors given database for certain fields and sends near real time notifications to specific user or
to a group chat with team members, so that everyone can monitor and track changes and react quickly if needed.

## Technical Side

This repo implements features as:
- authorization
- setup: choosing database, fields and place to send notifications (dms or group chat)
- tracking of changes in database pages

### Technologies Used
- aiohttp: as a web server
- rocketry: as a scheduler
- aiotg: as Telegram client
- notion-python: as Notion client
- poetry: as a dependency manager
- docker: as a containerization tool

## Usefule links
- [Accessing Notion API with Python](https://thienqc.notion.site/Notion-API-Python-ca0fd21bc224492b8daaf37eb06289e8)
- [Notion API Guide JS](https://developers.notion.com/docs/getting-started)
- [Notion API Raw Docs](https://developers.notion.com/reference)
- [Notion Postman](https://www.postman.com/notionhq/workspace/notion-s-api-workspace/overview)
- [Notion Python Client](https://github.com/ramnes/notion-sdk-py)
