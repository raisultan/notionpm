from aiogram import Bot, Dispatcher, types
from notion_client import Client
from notion_client.errors import UnauthorizedError
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.webhook import StopPropagation
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor, exceptions

NOTION_API_KEY = 'your-notion-api-key'

notion = Client(auth=NOTION_API_KEY)
bot = Bot(token='your-telegram-bot-token')
dp = Dispatcher(bot)


@dp.message_handler(Command('login'))
async def login(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    async with state.proxy() as data:
        data['telegram_id'] = message.from_user.id
        data['token'] = 'your-unique-token'

    auth_url = notion.oauth.auth_url(
        redirect_uri='https://your-redirect-uri.com/notion',  # Replace with your own redirect URI
        state=data['token'],
    )
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton(text="Login to Notion", url=auth_url))
    await message.reply("Click the button below to login to Notion", reply_markup=keyboard)


@dp.message_handler(Command('pages'))
async def pages(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    async with state.proxy() as data:
        access_token = data.get('access_token')
        if access_token is None:
            await message.reply("You need to login to Notion first")
            return

    try:
        database_id = 'your-database-id' # Replace with your own database ID
        results = notion.databases.query(
            **{
                "database_id": database_id,
                "filter": {
                    "property": "Property Name",
                    "title": {
                        "equals": "Property Value"
                    }
                },
                "sorts": [
                    {
                        "property": "Sort Name",
                        "direction": "asc"
                    }
                ],
                "start_cursor": access_token, # You can use access_token as start_cursor for pagination
                "page_size": 10,
            }
        ).get("results")

        # Do something with the results
        for result in results:
            title = result.properties['Title'].title[0].text.content
            await message.reply(title)

        # Save the latest access_token for pagination
        last_result = results[-1]
        async with state.proxy() as data:
            data['access_token'] = last_result.id

    except UnauthorizedError as e:
        await message.reply("Notion authorization failed")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
