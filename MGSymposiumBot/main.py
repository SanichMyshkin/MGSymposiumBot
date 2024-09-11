from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Event, EventSeries, init_db, get_db
from uuid import uuid4
from datetime import datetime

load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()  # Хранилище для FSM
dispatcher = Dispatcher(storage=storage)

logging.basicConfig(level=logging.INFO)

# Состояния для создания мероприятия
class CreateEventSeries(StatesGroup):
    waiting_for_name = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_description = State()
    waiting_for_image_url = State()

# Состояния для создания события
class CreateEvent(StatesGroup):
    waiting_for_series = State()
    waiting_for_event_name = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_room = State()
    waiting_for_speakers = State()
    waiting_for_description = State()
    waiting_for_image_url = State()

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
            f"Спикеры: {event.speakers or 'Не указаны'}\n"
            f"Описание: {event.description or 'Нет описания'}"
        )
        await callback.message.answer(details)

        # Если есть изображение, отправляем его
        if event.image_url:
            await callback.message.answer_photo(photo=event.image_url)
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
                message_text=(
                    f"Мероприятие: {event.event}\n"
                    f"Дата: {event.date}\n"
                    f"Время: {event.time}\n"
                    f"Место: {event.room}\n"
                    f"Спикеры: {event.speakers or 'Не указаны'}\n"
                    f"Описание: {event.description or 'Нет описания'}"
                )
            ),
            description=f"{event.date} {event.time} - {event.room}",
        )
        for event in events
    ]

    # Отправляем результаты в ответ на inline-запрос
    await inline_query.answer(results)

# Обработчик команды /create для начала создания мероприятия
@dispatcher.message(Command(commands=["create"]))
async def cmd_create(message: types.Message, state: FSMContext):
    await message.answer("Введите название мероприятия:")
    await state.set_state(CreateEventSeries.waiting_for_name)

# Обработчик для получения названия мероприятия
@dispatcher.message(CreateEventSeries.waiting_for_name)
async def event_series_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите дату начала мероприятия (в формате ГГГГ-ММ-ДД):")
    await state.set_state(CreateEventSeries.waiting_for_start_date)

# Обработчик для получения даты начала мероприятия
@dispatcher.message(CreateEventSeries.waiting_for_start_date)
async def event_series_start_date(message: types.Message, state: FSMContext):
    try:
        start_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        await state.update_data(start_date=start_date)
        await message.answer("Введите дату окончания мероприятия (в формате ГГГГ-ММ-ДД):")
        await state.set_state(CreateEventSeries.waiting_for_end_date)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз (ГГГГ-ММ-ДД).")

# Обработчик для получения даты окончания мероприятия
@dispatcher.message(CreateEventSeries.waiting_for_end_date)
async def event_series_end_date(message: types.Message, state: FSMContext):
    try:
        end_date = datetime.strptime(message.text, "%Y-%m-%d").date()
        data = await state.get_data()
        start_date = data['start_date']

        if end_date < start_date:
            await message.answer("Дата окончания не может быть раньше даты начала. Попробуйте снова.")
            return

        await state.update_data(end_date=end_date)
        await message.answer("Введите описание мероприятия:")
        await state.set_state(CreateEventSeries.waiting_for_description)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз (ГГГГ-ММ-ДД).")

# Обработчик для получения описания мероприятия
@dispatcher.message(CreateEventSeries.waiting_for_description)
async def event_series_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите ссылку на фотографию мероприятия (или пропустите шаг):")
    await state.set_state(CreateEventSeries.waiting_for_image_url)

# Обработчик для получения ссылки на изображение мероприятия
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

# Обработчик команды /create_event для начала создания события
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

# Обработчик для получения серии мероприятия
@dispatcher.callback_query(lambda c: c.data.startswith("select_series_"))
async def select_series(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[2])
    await state.update_data(series_id=series_id)
    await callback.message.answer("Введите название события:")
    await state.set_state(CreateEvent.waiting_for_event_name)

# Обработчики для сбора остальных данных события
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
    await message.answer("Введите имена спикеров (через запятую) или пропустите шаг:")
    await state.set_state(CreateEvent.waiting_for_speakers)

@dispatcher.message(CreateEvent.waiting_for_speakers)
async def event_speakers(message: types.Message, state: FSMContext):
    speakers = message.text if message.text else None
    await state.update_data(speakers=speakers)
    await message.answer("Введите описание события:")
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
        series_id=data['series_id'],
        event=data['event_name'],
        date=data['date'],
        time=data['time'],
        room=data['room'],
        speakers=data['speakers'],
        description=data['description'],
        image_url=image_url
    )
    db.add(new_event)
    db.commit()

    await message.answer(f"Событие '{data['event_name']}' добавлено.")
    await state.clear()

# Команда /delete для удаления мероприятия
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
        await state.set_state(DeleteEventSeries.waiting_for_series_to_delete)
    else:
        await message.answer("Нет доступных мероприятий для удаления.")

# Обработчик для выбора мероприятия, которое нужно удалить
@dispatcher.callback_query(lambda c: c.data.startswith("delete_series_"))
async def delete_series(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[2])
    await state.update_data(series_id=series_id)

    # Подтверждение удаления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да", callback_data="confirm_delete_series")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel_delete")]
    ])
    await callback.message.answer("Вы уверены, что хотите удалить это мероприятие и все его события?", reply_markup=keyboard)
    await state.set_state(DeleteEventSeries.waiting_for_confirmation)

# Обработчик подтверждения удаления мероприятия
@dispatcher.callback_query(lambda c: c.data == "confirm_delete_series")
async def confirm_delete_series(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    series_id = data['series_id']

    db: Session = next(get_db())
    series = db.query(EventSeries).filter(EventSeries.id == series_id).first()

    if series:
        # Удаление всех связанных событий
        db.query(Event).filter(Event.series_id == series_id).delete()
        # Удаление самого мероприятия
        db.delete(series)
        db.commit()
        await callback.message.answer(f"Мероприятие '{series.name}' и все его события удалены.")
    else:
        await callback.message.answer("Мероприятие не найдено.")

    await state.clear()

# Обработчик отмены удаления
@dispatcher.callback_query(lambda c: c.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление отменено.")
    await state.clear()

# Команда /delete_event для удаления события
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
        await state.set_state(DeleteEvent.waiting_for_event_to_delete)
    else:
        await message.answer("Нет доступных событий для удаления.")

# Обработчик для выбора события, которое нужно удалить
@dispatcher.callback_query(lambda c: c.data.startswith("delete_event_"))
async def delete_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[2])
    await state.update_data(event_id=event_id)

    # Подтверждение удаления
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да", callback_data="confirm_delete_event")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel_delete_event")]
    ])
    await callback.message.answer("Вы уверены, что хотите удалить это событие?", reply_markup=keyboard)
    await state.set_state(DeleteEvent.waiting_for_confirmation)

# Обработчик подтверждения удаления события
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

# Обработчик отмены удаления события
@dispatcher.callback_query(lambda c: c.data == "cancel_delete_event")
async def cancel_delete_event(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление события отменено.")
    await state.clear()

if __name__ == "__main__":
    init_db()  # Инициализация базы данных
    dispatcher.run_polling(bot)