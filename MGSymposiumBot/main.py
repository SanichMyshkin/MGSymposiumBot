import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, \
    InlineKeyboardButton, InlineKeyboardMarkup

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database import Event, EventSeries, get_db, init_db
from utils import is_url_valid, admin_only

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
            "/update - Редактировать существующиее мероприятие\n"
            "/update_event - Редактировать существующиее событие\n"
            "/id - Показать твое id (Нужно для администрирования бота)\n\n"
            "Что бы прервать создание или редактирование мероприятия/события - введите слово stop"
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
    events_series = db.query(EventSeries).filter(
        EventSeries.id == series_id).first()

    if events:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{event.event} ({event.date} {event.time})",
                callback_data=f"event_{event.id}")]
            for event in events
        ])
        if events_series.image_url and await is_url_valid(events_series.image_url):
            await callback.message.answer_photo(photo=events_series.image_url,
                                                caption=events_series.description,
                                                reply_markup=keyboard)
        else:
            await callback.message.answer(events_series.description, reply_markup=keyboard)
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

        if event.image_url and await is_url_valid(event.image_url):
            await callback.message.answer_photo(photo=event.image_url, caption=details)
        else:
            await callback.message.answer(details)
    else:
        await callback.message.answer("Событие не найдено.")


@dispatcher.message(Command(commands=["create"]))
@admin_only
async def cmd_create(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    await message.answer("Введите название мероприятия:")
    await state.set_state(CreateEventSeries.waiting_for_name)


@dispatcher.message(CreateEventSeries.waiting_for_name)
async def event_series_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    await state.update_data(name=message.text)
    await message.answer("Введите дату начала мероприятия (в формате ГГГГ-ММ-ДД):")
    await state.set_state(CreateEventSeries.waiting_for_start_date)


@dispatcher.message(CreateEventSeries.waiting_for_start_date)
async def event_series_start_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    try:
        start_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(start_date=start_date)
        await message.answer("Введите дату окончания мероприятия (в формате ГГГГ-ММ-ДД):")
        await state.set_state(CreateEventSeries.waiting_for_end_date)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз.")


@dispatcher.message(CreateEventSeries.waiting_for_end_date)
async def event_series_end_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

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
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    await state.update_data(description=message.text)
    await message.answer("Введите ссылку на фотографию мероприятия (или пропустите шаг):")
    await state.set_state(CreateEventSeries.waiting_for_image_url)


@dispatcher.message(CreateEventSeries.waiting_for_image_url)
async def event_series_image_url(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

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
@admin_only
async def cmd_create_event(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

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
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    await state.update_data(event_name=message.text)
    await message.answer("Введите дату события (в формате ГГГГ-ММ-ДД):")
    await state.set_state(CreateEvent.waiting_for_date)


@dispatcher.message(CreateEvent.waiting_for_date)
async def event_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    try:
        date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(date=date)
        await message.answer("Введите время события (в формате ЧЧ:ММ):")
        await state.set_state(CreateEvent.waiting_for_time)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз (ГГГГ-ММ-ДД).")


@dispatcher.message(CreateEvent.waiting_for_time)
async def event_time(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    try:
        time = datetime.strptime(message.text, "%H:%M").time()
        await state.update_data(time=time)
        await message.answer("Введите место проведения события:")
        await state.set_state(CreateEvent.waiting_for_room)
    except ValueError:
        await message.answer("Неправильный формат времени. Попробуйте еще раз (ЧЧ:ММ).")


@dispatcher.message(CreateEvent.waiting_for_room)
async def event_room(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    await state.update_data(room=message.text)
    await message.answer("Введите имена спикеров:")
    await state.set_state(CreateEvent.waiting_for_speakers)


@dispatcher.message(CreateEvent.waiting_for_speakers)
async def event_speakers(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    speakers = message.text if message.text else None
    await state.update_data(speakers=speakers)
    await message.answer("Введите описание события:")
    await state.set_state(CreateEvent.waiting_for_description)


@dispatcher.message(CreateEvent.waiting_for_description)
async def event_description(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    description = message.text if message.text else None
    await state.update_data(description=description)
    await message.answer("Введите ссылку на фотографию события:")
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
@admin_only
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
@admin_only
async def cmd_delete_event(message: types.Message, state: FSMContext):
    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()

    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"delete_event_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие, чтобы удалить событие:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для удаления событий.")


@dispatcher.callback_query(lambda c: c.data.startswith("delete_event_series_"))
async def select_event_series_to_delete_event(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])  # Извлекаем series_id
    await state.update_data(series_id=series_id)
    db: Session = next(get_db())
    events = db.query(Event).filter(Event.series_id == series_id).all()

    if events:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{event.event} ({event.date} {event.time})",
                callback_data=f"delete_selected_event_{event.id}")]
            for event in events
        ])
        await callback.message.answer("Выберите событие для удаления:", reply_markup=keyboard)
    else:
        await callback.message.answer("В этом мероприятии нет событий для удаления.")


@dispatcher.callback_query(lambda c: c.data.startswith("delete_selected_event_"))
async def delete_selected_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[3])
    await state.update_data(event_id=event_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да", callback_data="confirm_delete_event")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel_delete_event")]
    ])
    await callback.message.answer("Вы уверены, что хотите удалить это событие?", reply_markup=keyboard)


@dispatcher.callback_query(lambda c: c.data == "confirm_delete_event")
async def confirm_delete_event(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    event_id = data['event_id']

    db: Session = next(get_db())
    event = db.query(Event).filter(Event.id == event_id).first()

    if event:
        db.delete(event)
        db.commit()
        await callback.message.answer(f"Событие '{event.event}' успешно удалено.")
    else:
        await callback.message.answer("Событие не найдено.")
    await state.clear()


@dispatcher.callback_query(lambda c: c.data == "cancel_delete_event")
async def cancel_delete_event(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление события отменено.")
    await state.clear()


class UpdateEventSeries(StatesGroup):
    waiting_for_name = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_description = State()
    waiting_for_photo_url = State()


class UpdateEvent(StatesGroup):
    waiting_for_event_name = State()
    waiting_for_event_date = State()
    waiting_for_event_time = State()
    waiting_for_location = State()
    waiting_for_speakers = State()
    waiting_for_description = State()
    waiting_for_photo_url = State()


@dispatcher.message(Command(commands=["update"]))
@admin_only
async def cmd_update_event_series(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()

    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"update_event_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие для редактирования:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для редактирования.")


@dispatcher.callback_query(lambda c: c.data.startswith("update_event_series_"))
async def select_event_series_to_update(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])
    await state.update_data(series_id=series_id)
    await callback.message.answer("Введите новое название мероприятия:")
    await state.set_state(UpdateEventSeries.waiting_for_name)


@dispatcher.message(UpdateEventSeries.waiting_for_name)
async def update_event_series_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    new_name = message.text
    await state.update_data(new_name=new_name)
    await message.answer("Введите новую дату начала мероприятия (в формате YYYY-MM-DD):")
    await state.set_state(UpdateEventSeries.waiting_for_start_date)


@dispatcher.message(UpdateEventSeries.waiting_for_start_date)
async def update_event_series_start_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    new_start_date = message.text
    await state.update_data(new_start_date=new_start_date)
    await message.answer("Введите новую дату окончания мероприятия (в формате YYYY-MM-DD):")
    await state.set_state(UpdateEventSeries.waiting_for_end_date)


@dispatcher.message(UpdateEventSeries.waiting_for_end_date)
async def update_event_series_end_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    new_end_date = message.text
    await state.update_data(new_end_date=new_end_date)
    await message.answer("Введите новое описание мероприятия:")
    await state.set_state(UpdateEventSeries.waiting_for_description)


@dispatcher.message(UpdateEventSeries.waiting_for_description)
async def update_event_series_description(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    new_description = message.text
    await state.update_data(new_description=new_description)
    await message.answer("Введите новый URL фото мероприятия:")
    await state.set_state(UpdateEventSeries.waiting_for_photo_url)


@dispatcher.message(UpdateEventSeries.waiting_for_photo_url)
async def update_event_series_photo_url(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    new_image_url = message.text
    data = await state.get_data()
    series_id = data['series_id']
    new_name = data['new_name']
    new_start_date = data['new_start_date']
    new_end_date = data['new_end_date']
    new_description = data['new_description']

    db: Session = next(get_db())
    event_series = db.query(EventSeries).filter(
        EventSeries.id == series_id).first()

    if event_series:
        event_series.name = new_name
        event_series.start_date = new_start_date
        event_series.end_date = new_end_date
        event_series.description = new_description
        event_series.image_url = new_image_url
        db.commit()

        await message.answer(f"Мероприятие '{new_name}' успешно обновлено.")
    else:
        await message.answer("Мероприятие не найдено.")
    await state.clear()


@dispatcher.message(Command(commands=["update_event"]))
@admin_only
async def cmd_update_event(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()

    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"select_event_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие, в котором нужно обновить событие:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для обновления событий.")


@dispatcher.callback_query(lambda c: c.data.startswith("select_event_series_"))
async def select_event_series_for_update_event(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])
    await state.update_data(series_id=series_id)
    db: Session = next(get_db())
    events = db.query(Event).filter(Event.series_id == series_id).all()

    if events:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{event.event} ({event.date} {event.time})",
                callback_data=f"update_selected_event_{event.id}")]
            for event in events
        ])
        await callback.message.answer("Выберите событие для обновления:", reply_markup=keyboard)
    else:
        await callback.message.answer("Нет событий для обновления.")


@dispatcher.callback_query(lambda c: c.data.startswith("update_selected_event_"))
async def select_event_to_update(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[3])
    await state.update_data(event_id=event_id)
    await callback.message.answer("Введите новое название события:")
    await state.set_state(UpdateEvent.waiting_for_event_name)


@dispatcher.message(UpdateEvent.waiting_for_event_name)
async def update_event_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    new_event_name = message.text
    await state.update_data(new_event_name=new_event_name)
    await message.answer("Введите новую дату события (в формате YYYY-MM-DD):")
    await state.set_state(UpdateEvent.waiting_for_event_date)


@dispatcher.message(UpdateEvent.waiting_for_event_date)
async def update_event_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    new_event_date = message.text
    await state.update_data(new_event_date=new_event_date)
    await message.answer("Введите новое время события (в формате HH:MM):")
    await state.set_state(UpdateEvent.waiting_for_event_time)


@dispatcher.message(UpdateEvent.waiting_for_event_time)
async def update_event_time(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    new_event_time = message.text
    await state.update_data(new_event_time=new_event_time)
    await message.answer("Введите новое место проведения события:")
    await state.set_state(UpdateEvent.waiting_for_location)


@dispatcher.message(UpdateEvent.waiting_for_location)
async def update_event_location(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return
    new_location = message.text
    await state.update_data(new_location=new_location)
    await message.answer("Введите новых спикеров (через запятую):")
    await state.set_state(UpdateEvent.waiting_for_speakers)


@dispatcher.message(UpdateEvent.waiting_for_speakers)
async def update_event_speakers(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    new_speakers = message.text
    await state.update_data(new_speakers=new_speakers)
    await message.answer("Введите новое описание события:")
    await state.set_state(UpdateEvent.waiting_for_description)


@dispatcher.message(UpdateEvent.waiting_for_description)
async def update_event_description(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    new_description = message.text
    await state.update_data(new_description=new_description)
    await message.answer("Введите новый URL фото события:")
    await state.set_state(UpdateEvent.waiting_for_photo_url)


@dispatcher.message(UpdateEvent.waiting_for_photo_url)
async def update_event_photo_url(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    new_image_url = message.text
    data = await state.get_data()
    event_id = data['event_id']
    new_event_name = data['new_event_name']
    new_event_date = data['new_event_date']
    new_event_time = data['new_event_time']
    new_location = data['new_location']
    new_speakers = data['new_speakers']
    new_description = data['new_description']

    db: Session = next(get_db())
    event = db.query(Event).filter(Event.id == event_id).first()

    if event:
        event.event = new_event_name
        event.date = new_event_date
        event.time = new_event_time
        event.room = new_location
        event.speakers = new_speakers
        event.description = new_description
        event.image_url = new_image_url
        db.commit()

        await message.answer(f"Событие '{new_event_name}' успешно обновлено.")
    else:
        await message.answer("Событие не найдено.")
    await state.clear()


if __name__ == "__main__":
    init_db()

    async def main():
        await dispatcher.start_polling(bot)
    asyncio.run(main())
