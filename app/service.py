import asyncio

from aiohttp import web
from rocketry import Rocketry

from app.config import load_config
from app import setup
from app.routes import setup_routes

scheduler = Rocketry(config={'task_execution': 'async'})

async def start_rocketry(app: web.Application) -> None:
    app['rocketry_task'] = asyncio.create_task(scheduler.serve())


async def shutdown_rocketry(app: web.Application) -> None:
    scheduler.session.shut_down()
    app['rocketry_task'].cancel()


async def start_polling(app: web.Application) -> None:
    await app['dispatcher'].start_polling()


async def stop_polling(app: web.Application) -> None:
    app['dispatcher'].stop_polling()
    await app['dispatcher'].wait_closed()


def init_app(config: dict) -> web.Application:
    app = web.Application()
    app['config'] = config

    on_startup = [
        setup.storage,
        setup.notion_oauth,
        setup.dispatcher,
        setup.commands,
        start_rocketry,
        setup_routes,
        start_polling,
    ]
    client_context = [
        setup.bot,
        setup.redis,
    ]
    app.cleanup_ctx.extend(client_context)
    app.on_startup.extend(on_startup)
    app.on_shutdown.extend([stop_polling, shutdown_rocketry])

    return app


def start() -> None:
    config = load_config()
    app = init_app(config)

    web.run_app(app, port=8080, access_log=None)


if __name__ == '__main__':
    start()
