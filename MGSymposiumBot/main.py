from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
import logging
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from MGSymposiumBot.db import Event, init_db, get_db

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dispatcher = Dispatcher()


@dispatcher.message(Command(commands=["start"]))
async def cmd_start(message: Message):
    await message.answer("Привет! Чтобы добавить событие, используй команду /addevent.")


@dispatcher.message(Command(commands=["addevent"]))
async def cmd_addevent(message: Message):
    await message.answer("Введите данные события в формате: Дата (ГГГГ-ММ-ДД), Событие, Кабинет, Примечание")


@dispatcher.message()
async def cmd_add_event_data(message: Message):
    # Проверяем, что сообщение соответствует формату
    if len(message.text.split(',')) == 4:
        db: Session = next(get_db())
        date, event, room, note = map(str.strip, message.text.split(','))

        new_event = Event(date=date, event=event, room=room, note=note)

        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        await message.answer("Событие успешно добавлено!")
    else:
        await message.answer("Неверный формат! Введите данные в формате: Дата (ГГГГ-ММ-ДД), Событие, Кабинет, Примечание")


async def main():
    init_db()  # Инициализация базы данных
    await dispatcher.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Выход')
