from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery, InlineQuery, InlineQueryResultArticle, \
    InputTextMessageContent
from aiogram.fsm.context import FSMContext
import logging
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Event, EventSeries, init_db, get_db
from uuid import uuid4

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dispatcher = Dispatcher()

logging.basicConfig(level=logging.INFO)

# Команда /start для начала взаимодействия


@dispatcher.message(Command(commands=["start"]))
async def cmd_start(message: types.Message):
    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()

    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"Мероприятие: {series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Список мероприятий:", reply_markup=keyboard)
    else:
        await message.answer("Нет запланированных мероприятий.")

# Обработчик для отображения событий внутри выбранной серии мероприятий


@dispatcher.callback_query(lambda c: c.data.startswith("series_"))
async def show_events(callback: CallbackQuery):
    series_id = int(callback.data.split("_")[1])
    db: Session = next(get_db())

    # Получаем список событий для выбранной серии мероприятий
    events = db.query(Event).filter(Event.series_id == series_id).all()

    if events:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{event.event} ({event.date} {event.time})",
                callback_data=f"event_{event.id}")]
            for event in events
        ])
        await callback.message.answer("Список событий:", reply_markup=keyboard)
    else:
        await callback.message.answer("Нет событий в этом мероприятии.")

# Обработчик для отображения подробного описания события


@dispatcher.callback_query(lambda c: c.data.startswith("event_"))
async def show_event_details(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    db: Session = next(get_db())

    # Получаем подробную информацию о событии
    event = db.query(Event).filter(Event.id == event_id).first()

    if event:
        details = (
            f"Мероприятие: {event.event}\n"
            f"Дата: {event.date}\n"
            f"Время: {event.time}\n"
            f"Место: {event.room}\n"
            f"Спикеры: {event.speakers or 'Не указаны'}"
        )
        await callback.message.answer(details)
    else:
        await callback.message.answer("Событие не найдено.")

# Обработчик inline-запросов


@dispatcher.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    db: Session = next(get_db())
    events = db.query(Event).all()

    # Создаем inline результаты
    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=event.event,
            input_message_content=InputTextMessageContent(
                message_text=f"Мероприятие: {event.event}\nДата: {event.date}\nВремя: {event.time}\nМесто: {event.room}\nСпикеры: {event.speakers or 'Не указаны'}"
            ),
            description=f"{event.date} {event.time} - {event.room}",
        )
        for event in events
    ]

    # Отправляем результаты в ответ на inline-запрос
    await inline_query.answer(results)

# Запуск бота


async def main():
    init_db()
    await dispatcher.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Выход')
