import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Event, EventSeries, init_db, get_db
from datetime import datetime

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dispatcher = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)


class CreateEventSeries(StatesGroup):
    waiting_for_name = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_description = State()
    waiting_for_image_url = State()


class CreateEvent(StatesGroup):
    waiting_for_series = State()
    waiting_for_event_name = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_room = State()
    waiting_for_speakers = State()
    waiting_for_description = State()
    waiting_for_image_url = State()


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


@dispatcher.callback_query(lambda c: c.data.startswith("series_"))
async def show_events(callback: CallbackQuery):
    series_id = int(callback.data.split("_")[1])
    db: Session = next(get_db())
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


@dispatcher.callback_query(lambda c: c.data.startswith("event_"))
async def show_event_details(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    db: Session = next(get_db())
    event = db.query(Event).filter(Event.id == event_id).first()

    if event:
        details = (
            f"Мероприятие: {event.event}\n"
            f"Дата: {event.date}\n"
            f"Время: {event.time}\n"
            f"Место: {event.room}\n"
            f"Спикеры: {event.speakers or 'Не указаны'}\n"
            f"Описание: {event.description or 'Нет описания'}"
        )
        await callback.message.answer(details)
        if event.image_url:
            await callback.message.answer_photo(photo=event.image_url)
    else:
        await callback.message.answer("Событие не найдено.")


@dispatcher.message(Command(commands=["create"]))
async def cmd_create(message: types.Message, state: FSMContext):
    await message.answer("Введите название мероприятия:")
    await state.set_state(CreateEventSeries.waiting_for_name)


@dispatcher.message(CreateEventSeries.waiting_for_name)
async def event_series_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите дату начала мероприятия (в формате ГГГГ-ММ-ДД):")
    await state.set_state(CreateEventSeries.waiting_for_start_date)


@dispatcher.message(CreateEventSeries.waiting_for_start_date)
async def event_series_start_date(message: types.Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(start_date=start_date)
        await message.answer("Введите дату окончания мероприятия (в формате ГГГГ-ММ-ДД):")
        await state.set_state(CreateEventSeries.waiting_for_end_date)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз.")


@dispatcher.message(CreateEventSeries.waiting_for_end_date)
async def event_series_end_date(message: types.Message, state: FSMContext):
    try:
        end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        if end_date < data['start_date']:
            await message.answer("Дата окончания не может быть раньше даты начала.")
            return
        await state.update_data(end_date=end_date)
        await message.answer("Введите описание мероприятия:")
        await state.set_state(CreateEventSeries.waiting_for_description)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз.")


@dispatcher.message(CreateEventSeries.waiting_for_description)
async def event_series_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите ссылку на фотографию мероприятия (или пропустите шаг):")
    await state.set_state(CreateEventSeries.waiting_for_image_url)


@dispatcher.message(CreateEventSeries.waiting_for_image_url)
async def event_series_image_url(message: types.Message, state: FSMContext):
    image_url = message.text if message.text else None
    data = await state.get_data()
    db: Session = next(get_db())
    new_series = EventSeries(
        name=data['name'],
        start_date=data['start_date'],
        end_date=data['end_date'],
        description=data['description'],
        image_url=image_url
    )
    db.add(new_series)
    db.commit()
    await message.answer(f"Мероприятие '{data['name']}' создано.")
    await state.clear()


@dispatcher.message(Command(commands=["create_event"]))
async def cmd_create_event(message: types.Message, state: FSMContext):
    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()
    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"select_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие для добавления события:", reply_markup=keyboard)
        await state.set_state(CreateEvent.waiting_for_series)
    else:
        await message.answer("Нет доступных мероприятий для добавления событий.")


@dispatcher.callback_query(lambda c: c.data.startswith("select_series_"))
async def select_series(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[2])
    await state.update_data(series_id=series_id)
    await callback.message.answer("Введите название события:")
    await state.set_state(CreateEvent.waiting_for_event_name)


@dispatcher.message(CreateEvent.waiting_for_event_name)
async def event_name(message: types.Message, state: FSMContext):
    await state.update_data(event_name=message.text)
    await message.answer("Введите дату события (в формате ГГГГ-ММ-ДД):")
    await state.set_state(CreateEvent.waiting_for_date)


@dispatcher.message(CreateEvent.waiting_for_date)
async def event_date(message: types.Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(date=date)
        await message.answer("Введите время события (в формате ЧЧ:ММ):")
        await state.set_state(CreateEvent.waiting_for_time)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз (ГГГГ-ММ-ДД).")


@dispatcher.message(CreateEvent.waiting_for_time)
async def event_time(message: types.Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text, "%H:%M").time()
        await state.update_data(time=time)
        await message.answer("Введите место проведения события:")
        await state.set_state(CreateEvent.waiting_for_room)
    except ValueError:
        await message.answer("Неправильный формат времени. Попробуйте еще раз (ЧЧ:ММ).")


@dispatcher.message(CreateEvent.waiting_for_room)
async def event_room(message: types.Message, state: FSMContext):
    await state.update_data(room=message.text)
    await message.answer("Введите имена спикеров (или пропустите шаг):")
    await state.set_state(CreateEvent.waiting_for_speakers)


@dispatcher.message(CreateEvent.waiting_for_speakers)
async def event_speakers(message: types.Message, state: FSMContext):
    speakers = message.text if message.text else None
    await state.update_data(speakers=speakers)
    await message.answer("Введите описание события (или пропустите шаг):")
    await state.set_state(CreateEvent.waiting_for_description)


@dispatcher.message(CreateEvent.waiting_for_description)
async def event_description(message: types.Message, state: FSMContext):
    description = message.text if message.text else None
    await state.update_data(description=description)
    await message.answer("Введите ссылку на фотографию события (или пропустите шаг):")
    await state.set_state(CreateEvent.waiting_for_image_url)


@dispatcher.message(CreateEvent.waiting_for_image_url)
async def event_image_url(message: types.Message, state: FSMContext):
    image_url = message.text if message.text else None
    data = await state.get_data()
    db: Session = next(get_db())
    new_event = Event(
        event=data['event_name'],
        date=data['date'],
        time=data['time'],
        room=data['room'],
        speakers=data.get('speakers'),
        description=data.get('description'),
        image_url=image_url,
        series_id=data['series_id']
    )
    db.add(new_event)
    db.commit()
    await message.answer(f"Событие '{data['event_name']}' создано.")
    await state.clear()


@dispatcher.message(Command(commands=["delete"]))
async def cmd_delete_event_series(message: types.Message, state: FSMContext):
    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()

    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"delete_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие для удаления:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для удаления.")


@dispatcher.callback_query(lambda c: c.data.startswith("delete_series_"))
async def delete_series(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[2])
    await state.update_data(series_id=series_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да", callback_data="confirm_delete_series")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel_delete")]
    ])
    await callback.message.answer("Удалить мероприятие и все связанные события?", reply_markup=keyboard)


@dispatcher.callback_query(lambda c: c.data == "confirm_delete_series")
async def confirm_delete_series(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    series_id = data['series_id']
    db: Session = next(get_db())
    series = db.query(EventSeries).filter(EventSeries.id == series_id).first()

    if series:
        db.query(Event).filter(Event.series_id == series_id).delete()
        db.delete(series)
        db.commit()
        await callback.message.answer(f"Мероприятие '{series.name}' и все его события удалены.")
    else:
        await callback.message.answer("Мероприятие не найдено.")
    await state.clear()


@dispatcher.callback_query(lambda c: c.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление отменено.")
    await state.clear()


@dispatcher.message(Command(commands=["delete_event"]))
async def cmd_delete_event(message: types.Message, state: FSMContext):
    db: Session = next(get_db())
    events = db.query(Event).all()

    if events:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{event.event} ({event.date} {event.time})",
                callback_data=f"delete_event_{event.id}")]
            for event in events
        ])
        await message.answer("Выберите событие для удаления:", reply_markup=keyboard)
    else:
        await message.answer("Нет событий для удаления.")


@dispatcher.callback_query(lambda c: c.data.startswith("delete_event_"))
async def delete_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[2])
    await state.update_data(event_id=event_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да", callback_data="confirm_delete_event")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel_delete_event")]
    ])
    await callback.message.answer("Удалить это событие?", reply_markup=keyboard)


@dispatcher.callback_query(lambda c: c.data == "confirm_delete_event")
async def confirm_delete_event(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    event_id = data['event_id']
    db: Session = next(get_db())
    event = db.query(Event).filter(Event.id == event_id).first()

    if event:
        db.delete(event)
        db.commit()
        await callback.message.answer(f"Событие '{event.event}' удалено.")
    else:
        await callback.message.answer("Событие не найдено.")
    await state.clear()


@dispatcher.callback_query(lambda c: c.data == "cancel_delete_event")
async def cancel_delete_event(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление события отменено.")
    await state.clear()

if __name__ == "__main__":
    init_db()

    async def main():
        await dispatcher.start_polling(bot)

    asyncio.run(main())
