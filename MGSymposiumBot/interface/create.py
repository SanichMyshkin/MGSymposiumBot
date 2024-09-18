# create.py
from datetime import datetime, time

from sqlalchemy.future import select
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from models import Event, EventSeries, get_db
from utils import admin_only, format_date, check_optional_field
from states import CreateEvent, CreateEventSeries


def register_create_cmd(dp: Dispatcher):
    dp.message.register(cmd_create, Command(commands=["create"]))
    dp.message.register(cmd_create_event, Command(commands=["create_event"]))
    dp.message.register(event_series_name, CreateEventSeries.waiting_for_name)
    dp.message.register(event_series_start_date,
                        CreateEventSeries.waiting_for_start_date)
    dp.message.register(event_series_end_date,
                        CreateEventSeries.waiting_for_end_date)
    dp.message.register(event_series_description,
                        CreateEventSeries.waiting_for_description)
    dp.message.register(event_series_image_url,
                        CreateEventSeries.waiting_for_image_url)
    dp.callback_query.register(
        select_series, lambda c: c.data.startswith("select_series_"))
    dp.message.register(event_name, CreateEvent.waiting_for_event_name)
    dp.message.register(event_date, CreateEvent.waiting_for_date)
    dp.message.register(event_time, CreateEvent.waiting_for_time)
    dp.message.register(event_room, CreateEvent.waiting_for_room)
    dp.message.register(event_speakers, CreateEvent.waiting_for_speakers)
    dp.message.register(event_description, CreateEvent.waiting_for_description)
    dp.message.register(event_image_url, CreateEvent.waiting_for_image_url)


@admin_only
async def cmd_create(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    await message.answer("Введите название мероприятия:")
    await state.set_state(CreateEventSeries.waiting_for_name)


async def event_series_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    await state.update_data(name=message.text)
    await message.answer("Введите дату начала мероприятия (в формате ДД.ММ.ГГГГ):")
    await state.set_state(CreateEventSeries.waiting_for_start_date)


async def event_series_start_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(start_date=start_date)
        await message.answer("Введите дату окончания мероприятия (в формате ДД.ММ.ГГГГ):")
        await state.set_state(CreateEventSeries.waiting_for_end_date)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз. Формат должен быть: ДД.ММ.ГГГГ.")


async def event_series_end_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    try:
        data = await state.get_data()
        start_date = data['start_date']

        end_date = datetime.strptime(message.text, "%d.%m.%Y").date()

        if end_date < start_date:
            await message.answer("Дата окончания не может быть раньше даты начала.")
            return

        await state.update_data(end_date=end_date)
        await message.answer("Введите описание мероприятия (или '-' для пропуска):")
        await state.set_state(CreateEventSeries.waiting_for_description)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз. Формат должен быть: ДД.ММ.ГГГГ.")


async def event_series_description(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание мероприятия прервано.")
        return

    description = check_optional_field(message.text)
    await state.update_data(description=description)
    await message.answer("Загрузите фотографию для мероприятия (или '-' для пропуска):")
    await state.set_state(CreateEventSeries.waiting_for_image_url)


async def event_series_image_url(message: types.Message, state: FSMContext):
    if text := message.text:
        if text.lower() == "stop":
            await state.clear()
            await message.answer("Создание мероприятия прервано.")
            return

    data = await state.get_data()

    async for db in get_db():
        new_series = EventSeries(
            name=data['name'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            description=data['description'],
            image_url=message.photo[-1].file_id if message.photo else None,
        )

        db.add(new_series)
        await db.commit()
        await db.close()

    await message.answer(f"Мероприятие '{data['name']}' создано.")
    await state.clear()


@admin_only
async def cmd_create_event(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание события прервано.")
        return

    db: AsyncSession = await get_db().__anext__()
    event_series = await get_event_series(db)
    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name}: {format_date(series.start_date, series.end_date)}",
                callback_data=f"select_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие для добавления события:", reply_markup=keyboard)
        await state.set_state(CreateEvent.waiting_for_series)
    else:
        await message.answer("Нет доступных мероприятий для добавления событий.")
    await db.close()


async def get_event_series(db: AsyncSession):
    result = await db.execute(select(EventSeries))
    event_series = result.scalars().all()
    return event_series


async def select_series(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[2])
    await state.update_data(series_id=series_id)
    await callback.message.answer("Введите название события:")
    await state.set_state(CreateEvent.waiting_for_event_name)


async def event_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание события прервано.")
        return
    await state.update_data(event_name=message.text)
    await message.answer("Введите дату события (в формате ДД.ММ.ГГГГ):")
    await state.set_state(CreateEvent.waiting_for_date)


async def event_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание события прервано.")
        return
    try:
        date = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(date=date)
        await message.answer("Введите время события (в формате ЧЧ:ММ - ЧЧ:ММ):")
        await state.set_state(CreateEvent.waiting_for_time)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте еще раз (ДД.ММ.ГГГГ).")


async def event_time(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание события прервано.")
        return

    time_input = message.text.strip()

    try:
        start_time, end_time = time_input.split('-')
        start_time = start_time.strip()
        end_time = end_time.strip()

        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))

        start_time_obj = time(start_hour, start_minute)
        end_time_obj = time(end_hour, end_minute)

        if start_time_obj >= end_time_obj:
            await message.answer("Время начала не может быть позже или равно времени окончания. Попробуйте снова.")
            return

        await state.update_data(time=f"{start_time_obj.strftime('%H:%M')} - {end_time_obj.strftime('%H:%M')}")

        await message.answer("Введите место проведения события:")
        await state.set_state(CreateEvent.waiting_for_room)

    except ValueError:
        await message.answer("Неправильный формат времени. Попробуйте еще раз (ЧЧ:ММ - ЧЧ:ММ).")


async def event_room(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание события прервано.")
        return
    await state.update_data(room=message.text)
    await message.answer("Введите имена спикеров или '-' для пропуска:")
    await state.set_state(CreateEvent.waiting_for_speakers)


async def event_speakers(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание события прервано.")
        return

    speakers = message.text if message.text != "-" else "-"
    await state.update_data(speakers=speakers)
    await message.answer("Введите описание события или '-' для пропуска:")
    await state.set_state(CreateEvent.waiting_for_description)


async def event_description(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Создание события прервано.")
        return

    description = message.text
    await state.update_data(description=description)
    await message.answer("Загрузите фотографию для события (или '-' для пропуска)")
    await state.set_state(CreateEvent.waiting_for_image_url)


async def event_image_url(message: types.Message, state: FSMContext):
    if text := message.text:
        if text.lower() == "stop":
            await state.clear()
            await message.answer("Создание события прервано.")
            return

    data = await state.get_data()
    async for db in get_db():
        new_event = Event(
            event=data['event_name'],
            date=data['date'],
            time=data['time'],
            room=data['room'],
            speakers=data.get('speakers'),
            description=data.get('description'),
            image_url=message.photo[-1].file_id if message.photo else None,
            series_id=data['series_id'])

        db.add(new_event)
        await db.commit()

    await message.answer(f"Событие '{data['event_name']}' создано.")
    await state.clear()

    await db.close()
