import asyncio
import signal

from aiohttp import web
from app.notifications import app as notification_app

from app.initializer import bot, redis
from app.dispatcher import setup_dispatcher, connect_notion

dp = setup_dispatcher()


async def main():
    global app
    app = web.Application()
    app.add_routes([web.get("/oauth/callback", connect_notion.handle_oauth)])

    global runner
    runner = web.AppRunner(app)
    await runner.setup()

    global tcp_server
    tcp_server = web.TCPSite(runner, "localhost", 8080)

    global notification_app
    notification_app = asyncio.create_task(notification_app.session.scheduler.serve())

    await tcp_server.start()
    await dp.start_polling()


async def shutdown(signal, loop):
    print(f"\nReceived {signal.name} signal, shutting down...")
    await redis.close()
    notification_app.cancel()

    dp.stop_polling()
    await dp.wait_closed()
    await bot.close()

    await tcp_server.stop()
    await runner.cleanup()
    await app.cleanup()
    await loop.shutdown_asyncgens()
    loop.stop()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    for signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signal, lambda s=signal: asyncio.create_task(shutdown(s, loop)))

    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
        print("Application has been shut down.")
