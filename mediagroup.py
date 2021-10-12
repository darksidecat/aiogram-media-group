from typing import List, Optional

from aiogram.types import Chat, Message, Update, User
from aiogram.types.base import TelegramObject


class MediaGroup(TelegramObject):
    media_group_id: str
    chat: Chat
    from_user: Optional[User]
    messages: List[Message]


class MediaGroupUpdate(Update):
    media_group: MediaGroup

    def __init__(self, update_id: int, media_group: MediaGroup):
        super().__init__(update_id=update_id, media_group=media_group)

    @property
    def event_type(self) -> str:
        return "media_group"

    @property
    def event(self) -> MediaGroup:
        return self.media_group
