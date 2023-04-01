import os
from aiohttp import web
from aiohttp.web_request import Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.dispatcher.webhook import SendMessage
from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=os.environ["BOT_TOKEN"])
dp = Dispatcher(bot)

NOTION_CLIENT_ID = os.environ['OAUTH_CLIENT_ID']
NOTION_REDIRECT_URI = 'https://notionpm.xyz/oauth/callback'

async def handle(request: Request):
    if request.method == 'GET':
        code = request.query.get('code')
        update = types.Update(code)
        await dp.process_update(update)
        return web.Response(status=200)
    else:
        return web.Response(status=405)

async def send_welcome(message: types.Message):
    await bot.send_message(message.chat.id, "Hi there! I'm a bot that can help you with Notion OAuth login. Just type /login to get started.")

async def send_login_url(message: types.Message):
    login_url = f'https://api.notion.com/v1/oauth/authorize?client_id={NOTION_CLIENT_ID}&redirect_uri={NOTION_REDIRECT_URI}&response_type=code'
    await bot.send_message(message.chat.id, f'Click the link to login to Notion:\n\n{login_url}', parse_mode=ParseMode.HTML)

dp.register_message_handler(send_welcome, commands=['start'])
dp.register_message_handler(send_login_url, commands=['login'])

if __name__ == '__main__':
    async def main():
        app = web.Application()
        app.add_routes([web.get('/oauth/callback', handle)])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        await site.start()
        await dp.start_polling()

    # Run the main coroutine until it completes
    import asyncio
    asyncio.run(main())
