import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.dispatcher.event.telegram import TelegramEventObserver
from aiogram.dispatcher.fsm.middleware import FSMContextMiddleware
from aiogram.types import InputMediaPhoto

from mediagroup import MediaGroup
from mediagroup_middleware import MediaGroupMiddleware

TOKEN = "TOKEN HERE"


async def media_handler_with_filter(media_group: MediaGroup, bot: Bot):
    await bot.send_message(
        media_group.chat.id, "Mediagroup may contain at lest one photo"
    )


async def media_handler(media_group: MediaGroup, bot: Bot):
    photos_ids = []
    for message in media_group.messages:
        if message.photo:
            photos_ids.append(message.photo[-1].file_id)

    images_media = [InputMediaPhoto(media=photo_id) for photo_id in photos_ids]
    await bot.send_media_group(media_group.chat.id, images_media)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    bot = Bot(TOKEN)
    dp = Dispatcher(isolate_events=True)

    fsm_middleware_position = None
    isolate_events = False
    for i, middleware in enumerate(dp.update.outer_middlewares):
        if isinstance(middleware, FSMContextMiddleware):
            fsm_middleware_position = i
            isolate_events = middleware.isolate_events

    mediagroup_middleware = MediaGroupMiddleware(dp, collect_time=0.2)

    # if isolate events enabled then we register MediaGroupMiddleware before FSMContextMiddleware
    if fsm_middleware_position and isolate_events:
        dp.update.outer_middlewares.insert(
            fsm_middleware_position, mediagroup_middleware
        )
    else:
        dp.update.outer_middleware(mediagroup_middleware)

    dp.media_group = dp.observers["media_group"] = TelegramEventObserver(
        router=dp, event_name="media_group"
    )

    dp.media_group.register(
        media_handler_with_filter,
        lambda m: not (any(message.photo for message in m.messages)),
    )
    dp.media_group.register(media_handler)

    try:
        await bot.get_updates(offset=-1)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
