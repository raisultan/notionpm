from aiogram import types

import app.storage as storage


async def skip_or_continue_setup(message: types.Message):
    from app.commands.connect_notion import send_login_url
    from app.dispatcher import choose_database, choose_properties

    access_token = await storage.get_user_access_token(message.chat.id)
    if not access_token:
        await send_login_url(message)
        await storage.set_user_setup_status(message.chat.id, True)
        return

    db_id = await storage.get_user_db_id(message.chat.id)
    if not db_id:
        await choose_database.execute(message)
        await storage.set_user_setup_status(message.chat.id, True)
        return

    tracked_properties = await storage.get_user_tracked_properties(message.chat.id)
    if not tracked_properties:
        await choose_properties.execute(message)
        await storage.set_user_setup_status(message.chat.id, True)
        return

    await storage.set_user_setup_status(message.chat.id, False)
