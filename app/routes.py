from aiohttp import web
import aiohttp_cors


async def setup_routes(app: web.Application) -> None:
    """Инициализация эндпоинтов веб приложения."""
    cors = aiohttp_cors.setup(app, defaults={
        '*': aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers='*',
            allow_headers='*',
        ),
    })

    cors.add(app.router.add_get('/oauth/callback', app['connect_notion'].handle_oauth))
