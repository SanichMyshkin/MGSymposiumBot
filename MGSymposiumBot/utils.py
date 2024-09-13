import aiohttp
import os

from functools import wraps
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv()


ADMIN_ID = os.getenv('OWNER_ID')


async def is_url_valid(url: str) -> bool:
    """Проверяет, доступен ли URL (ответ с кодом 200)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as response:
                return response.status == 200
    except Exception as e:
        print(f"Error checking URL: {e}")
        return False


def admin_only(func):
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        if str(message.from_user.id) == ADMIN_ID:
            return await func(message, *args, **kwargs)
        else:
            await message.answer("Извините, у вас нет доступа к этой команде.")
    return wrapper
