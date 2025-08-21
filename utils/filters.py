from aiogram.filters import Filter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramNotFound
from aiogram.enums.chat_type import ChatType
from main import bot
from config import  administrators


class IsPrivate(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.chat.type == ChatType.PRIVATE

class IsAdmin(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in administrators

