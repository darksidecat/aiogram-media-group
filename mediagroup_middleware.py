import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, cast

from aiogram import BaseMiddleware, Dispatcher
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.types import Message, Update

from mediagroup import MediaGroup, MediaGroupUpdate

logger = logging.getLogger(__name__)


@dataclass
class MediaGroupData:
    first_message: int
    messages: List[Message]
    handled: Optional[bool]
    lock: bool = False


class MediaGroupMiddleware(BaseMiddleware):
    def __init__(self, dp: Dispatcher, collect_time: float = 1.0) -> None:
        self.dp = dp
        self.media_groups: Dict[str, MediaGroupData] = {}
        self.collect_time = collect_time

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:

        if event.event_type != "message":
            return await handler(event, data)

        message = cast(Message, event.event)

        if not message.media_group_id:
            return await handler(event, data)

        media_group_id = message.media_group_id
        # first message in media_group create MediaGroupData
        if not self.media_groups.get(media_group_id):
            self.media_groups[media_group_id] = MediaGroupData(
                first_message=message.message_id, messages=[], handled=None
            )

        media_group_data = self.media_groups[media_group_id]

        if not media_group_data.lock:  # check if media group was not sent to dispatcher
            media_group_data.messages.append(message)

        if message.message_id == media_group_data.first_message:
            # wait for group collecting for collect_time
            await asyncio.sleep(self.collect_time)

            media_group = MediaGroup(
                media_group_id=media_group_id,
                chat=message.chat,
                from_user=message.from_user,
                messages=media_group_data.messages,
            )
            media_group_update = MediaGroupUpdate(
                event.update_id, media_group=media_group
            )

            # disable adding messages in media_group permission before send update to dispatcher
            media_group_data.lock = True
            response = await self.dp.propagate_event(
                "update",
                media_group_update,
                **data,
            )
            media_group_data.messages.remove(message)  # cleanup

            # set handled flag for logging updates handling
            if response is UNHANDLED:
                media_group_data.handled = False
                return UNHANDLED
            else:
                media_group_data.handled = True

        else:
            # wait for media group handling result
            while media_group_data.handled is None:
                await asyncio.sleep(self.collect_time)

            try:
                # if not enough time for group collect return UNHANDLED for missed messages
                if message not in media_group_data.messages:
                    logger.warning(
                        "Missed message in media group, please increase collect_time"
                    )
                    return UNHANDLED

                media_group_data.messages.remove(message)  # cleanup
                if media_group_data.handled is False:
                    return UNHANDLED
            finally:
                if not media_group_data.messages:  # cleanup
                    del media_group_data
