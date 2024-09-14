import aiohttp
import os

from functools import wraps
from aiogram.types import Message
from dotenv import load_dotenv
from datetime import datetime

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


months_genitive = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}


def format_date(start_date: datetime, end_date: datetime):
    if start_date == end_date:
        return f"{start_date.day} {months_genitive[start_date.month]}"
    if start_date.year == end_date.year:
        if start_date.month == end_date.month:
            return (f"{start_date.day} - {end_date.day}"
                    f" {months_genitive[start_date.month]}")
        else:
            return (f"{start_date.day}"
                    f" {months_genitive[start_date.month]} - "
                    f"{end_date.day} {months_genitive[end_date.month]}")
    else:
        return (f"{start_date.day} {months_genitive[start_date.month]}"
                f" {start_date.year} года - {end_date.day}"
                f" {months_genitive[end_date.month]} {end_date.year} года")


def check_optional_field(field: str) -> str:
    return None if field.strip() == "-" else field