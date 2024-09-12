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
        await callback.message.answer(f"Список событий:{events}", reply_markup=keyboard)
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
    event_series = db.query(EventSeries).all()

    if event_series:
        # Генерируем список мероприятий для удаления события
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"delete_event_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие, чтобы удалить событие:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для удаления событий.")

# Шаг 2: Обработчик выбора мероприятия для удаления события


@dispatcher.callback_query(lambda c: c.data.startswith("delete_event_series_"))
async def select_event_series_to_delete_event(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])  # Извлекаем series_id
    await state.update_data(series_id=series_id)

    # Получаем события для выбранного мероприятия
    db: Session = next(get_db())
    events = db.query(Event).filter(Event.series_id == series_id).all()

    if events:
        # Генерируем список событий для удаления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{event.event} ({event.date} {event.time})",
                callback_data=f"delete_selected_event_{event.id}")]
            for event in events
        ])
        await callback.message.answer("Выберите событие для удаления:", reply_markup=keyboard)
    else:
        await callback.message.answer("В этом мероприятии нет событий для удаления.")

# Шаг 3: Обработчик выбора конкретного события для удаления


@dispatcher.callback_query(lambda c: c.data.startswith("delete_selected_event_"))
async def delete_selected_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[3])  # Извлекаем event_id
    await state.update_data(event_id=event_id)

    # Подтверждение удаления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да", callback_data="confirm_delete_event")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel_delete_event")]
    ])
    await callback.message.answer("Вы уверены, что хотите удалить это событие?", reply_markup=keyboard)

# Шаг 4: Подтверждение удаления события


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

# Шаг 5: Отмена удаления события


@dispatcher.callback_query(lambda c: c.data == "cancel_delete_event")
async def cancel_delete_event(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление события отменено.")
    await state.clear()


# Машина состояний для обновления мероприятия
class UpdateEventSeries(StatesGroup):
    waiting_for_name = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_description = State()
    waiting_for_photo_url = State()

# Машина состояний для обновления события


class UpdateEvent(StatesGroup):
    waiting_for_event_name = State()
    waiting_for_event_date = State()
    waiting_for_event_time = State()
    waiting_for_location = State()
    waiting_for_speakers = State()
    waiting_for_description = State()
    waiting_for_photo_url = State()

# Команды для обновления мероприятия

# Шаг 1: Команда /update для начала процесса обновления мероприятия


@dispatcher.message(Command(commands=["update"]))
async def cmd_update_event_series(message: types.Message, state: FSMContext):
    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()

    if event_series:
        # Генерируем список мероприятий для обновления
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"update_event_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие для редактирования:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для редактирования.")

# Шаг 2: Обработчик выбора мероприятия для редактирования


@dispatcher.callback_query(lambda c: c.data.startswith("update_event_series_"))
async def select_event_series_to_update(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])  # Извлекаем series_id
    await state.update_data(series_id=series_id)

    # Запрашиваем новое название мероприятия
    await callback.message.answer("Введите новое название мероприятия:")
    await state.set_state(UpdateEventSeries.waiting_for_name)

# Шаг 3: Обновление названия мероприятия


@dispatcher.message(UpdateEventSeries.waiting_for_name)
async def update_event_series_name(message: types.Message, state: FSMContext):
    new_name = message.text
    await state.update_data(new_name=new_name)

    # Запрашиваем новую дату начала
    await message.answer("Введите новую дату начала мероприятия (в формате YYYY-MM-DD):")
    await state.set_state(UpdateEventSeries.waiting_for_start_date)

# Шаг 4: Обновление даты начала мероприятия


@dispatcher.message(UpdateEventSeries.waiting_for_start_date)
async def update_event_series_start_date(message: types.Message, state: FSMContext):
    new_start_date = message.text
    await state.update_data(new_start_date=new_start_date)

    # Запрашиваем новую дату окончания
    await message.answer("Введите новую дату окончания мероприятия (в формате YYYY-MM-DD):")
    await state.set_state(UpdateEventSeries.waiting_for_end_date)

# Шаг 5: Обновление даты окончания мероприятия


@dispatcher.message(UpdateEventSeries.waiting_for_end_date)
async def update_event_series_end_date(message: types.Message, state: FSMContext):
    new_end_date = message.text
    await state.update_data(new_end_date=new_end_date)

    # Запрашиваем новое описание
    await message.answer("Введите новое описание мероприятия:")
    await state.set_state(UpdateEventSeries.waiting_for_description)

# Шаг 6: Обновление описания мероприятия


@dispatcher.message(UpdateEventSeries.waiting_for_description)
async def update_event_series_description(message: types.Message, state: FSMContext):
    new_description = message.text
    await state.update_data(new_description=new_description)

    # Запрашиваем новый URL фото
    await message.answer("Введите новый URL фото мероприятия (или отправьте 'none' для отсутствия фото):")
    await state.set_state(UpdateEventSeries.waiting_for_photo_url)

# Шаг 7: Обновление URL фото и сохранение изменений


@dispatcher.message(UpdateEventSeries.waiting_for_photo_url)
async def update_event_series_photo_url(message: types.Message, state: FSMContext):
    new_image_url = message.text
    if new_image_url.lower() == 'none':
        new_image_url = None

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

# Команды для обновления события

# Шаг 1: Команда /update_event для начала процесса обновления события


@dispatcher.message(Command(commands=["update_event"]))
async def cmd_update_event(message: types.Message, state: FSMContext):
    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()

    if event_series:
        # Генерируем список мероприятий
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"select_event_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие, в котором нужно обновить событие:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для обновления событий.")

# Шаг 2: Обработчик выбора мероприятия для редактирования события


@dispatcher.callback_query(lambda c: c.data.startswith("select_event_series_"))
async def select_event_series_for_update_event(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])
    await state.update_data(series_id=series_id)

    # Получаем список событий
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

# Шаг 3: Обработчик выбора события для обновления


@dispatcher.callback_query(lambda c: c.data.startswith("update_selected_event_"))
async def select_event_to_update(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[3])
    await state.update_data(event_id=event_id)

    # Запрашиваем новое название события
    await callback.message.answer("Введите новое название события:")
    await state.set_state(UpdateEvent.waiting_for_event_name)

# Шаг 4: Обновление названия события


@dispatcher.message(UpdateEvent.waiting_for_event_name)
async def update_event_name(message: types.Message, state: FSMContext):
    new_event_name = message.text
    await state.update_data(new_event_name=new_event_name)

    # Запрашиваем новую дату события
    await message.answer("Введите новую дату события (в формате YYYY-MM-DD):")
    await state.set_state(UpdateEvent.waiting_for_event_date)

# Шаг 5: Обновление даты события


@dispatcher.message(UpdateEvent.waiting_for_event_date)
async def update_event_date(message: types.Message, state: FSMContext):
    new_event_date = message.text
    await state.update_data(new_event_date=new_event_date)

    # Запрашиваем новое время события
    await message.answer("Введите новое время события (в формате HH:MM):")
    await state.set_state(UpdateEvent.waiting_for_event_time)

# Шаг 6: Обновление времени события


@dispatcher.message(UpdateEvent.waiting_for_event_time)
async def update_event_time(message: types.Message, state: FSMContext):
    new_event_time = message.text
    await state.update_data(new_event_time=new_event_time)

    # Запрашиваем новое место проведения
    await message.answer("Введите новое место проведения события:")
    await state.set_state(UpdateEvent.waiting_for_location)

# Шаг 7: Обновление места проведения


@dispatcher.message(UpdateEvent.waiting_for_location)
async def update_event_location(message: types.Message, state: FSMContext):
    new_location = message.text
    await state.update_data(new_location=new_location)

    # Запрашиваем новых спикеров
    await message.answer("Введите новых спикеров (через запятую):")
    await state.set_state(UpdateEvent.waiting_for_speakers)

# Шаг 8: Обновление спикеров


@dispatcher.message(UpdateEvent.waiting_for_speakers)
async def update_event_speakers(message: types.Message, state: FSMContext):
    new_speakers = message.text
    await state.update_data(new_speakers=new_speakers)

    # Запрашиваем новое описание события
    await message.answer("Введите новое описание события:")
    await state.set_state(UpdateEvent.waiting_for_description)

# Шаг 9: Обновление описания события


@dispatcher.message(UpdateEvent.waiting_for_description)
async def update_event_description(message: types.Message, state: FSMContext):
    new_description = message.text
    await state.update_data(new_description=new_description)

    # Запрашиваем новый URL фото
    await message.answer("Введите новый URL фото события (или отправьте 'none' для отсутствия фото):")
    await state.set_state(UpdateEvent.waiting_for_photo_url)

# Шаг 10: Обновление URL фото и сохранение изменений


@dispatcher.message(UpdateEvent.waiting_for_photo_url)
async def update_event_photo_url(message: types.Message, state: FSMContext):
    new_image_url = message.text
    if new_image_url.lower() == 'none':
        new_image_url = None

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
