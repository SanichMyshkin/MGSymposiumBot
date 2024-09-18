import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

from dotenv import load_dotenv

from models import init_db
from interface.read import register_read_cmd
from interface.create import register_create_cmd
from interface.update import register_update_cmd
from interface.delete import register_delete_cmd

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
logo = os.getenv('MGSU_DEFAULT_LOGO')
storage = MemoryStorage()
dispatcher = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)


@dispatcher.message(Command(commands=["help"]))
async def cmd_help(message: types.Message):
    if os.getenv("OWNER_ID") == str(message.from_user.id):
        help_text = (
            "Доступные команды:\n"
            "/help - Показать это сообщение\n"
            "/start - Показать список мероприятий\n"
            "/create - Создать новое мероприятие\n"
            "/create_event - Создать событие внутри мероприятия\n"
            "/delete - Удалить мероприятие и все связанные с ним события \n"
            "/delete_event - Удалить событие\n"
            "/update - Редактировать существующее мероприятие\n"
            "/update_event - Редактировать существующее событие\n"
            "/id - Показать твой ID (Нужно для администрирования бота)\n\n"
            "Чтобы прервать создание или редактирование мероприятия/события - введите слово stop"
        )
    else:
        help_text = (
            "Доступные команды:\n"
            "/start - Показать список мероприятий\n"
            "/help - Показать это сообщение\n"
        )
    await message.answer(help_text)


@dispatcher.message(Command(commands=["id"]))
async def cmd_id(message: types.Message):
    user_id = message.from_user.id
    await message.answer(f"Ваш ID пользователя: {user_id}")


def register_handlers():
    register_read_cmd(dispatcher)
    register_create_cmd(dispatcher)
    register_update_cmd(dispatcher)
    register_delete_cmd(dispatcher)


async def main():
    await init_db()  # Добавляем await
    register_handlers()
    await dispatcher.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
