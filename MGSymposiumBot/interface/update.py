from datetime import datetime
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models import Event, EventSeries, get_db
from utils import admin_only, format_date
from states import UpdateEvent, UpdateEventSeries


def register_update_cmd(dp: Dispatcher):
    dp.message.register(cmd_update_event_series, Command(commands=["update"]))
    dp.callback_query.register(
        select_event_series_to_update, lambda c: c.data.startswith("update_event_series_"))
    dp.message.register(update_event_series_name,
                        UpdateEventSeries.waiting_for_name)
    dp.message.register(update_event_series_start_date,
                        UpdateEventSeries.waiting_for_start_date)
    dp.message.register(update_event_series_end_date,
                        UpdateEventSeries.waiting_for_end_date)
    dp.message.register(update_event_series_description,
                        UpdateEventSeries.waiting_for_description)
    dp.message.register(update_event_series_photo_url,
                        UpdateEventSeries.waiting_for_photo_url)

    dp.message.register(cmd_update_event, Command(commands=["update_event"]))
    dp.callback_query.register(select_event_series_for_update_event,
                               lambda c: c.data.startswith("select_event_series_"))
    dp.callback_query.register(
        select_event_to_update, lambda c: c.data.startswith("update_selected_event_"))
    dp.message.register(update_event_name, UpdateEvent.waiting_for_event_name)
    dp.message.register(update_event_date, UpdateEvent.waiting_for_event_date)
    dp.message.register(update_event_time, UpdateEvent.waiting_for_event_time)
    dp.message.register(update_event_location,
                        UpdateEvent.waiting_for_location)
    dp.message.register(update_event_description,
                        UpdateEvent.waiting_for_description)
    dp.message.register(update_event_speakers,
                        UpdateEvent.waiting_for_speakers)
    dp.message.register(update_event_photo_url,
                        UpdateEvent.waiting_for_photo_url)


@admin_only
async def cmd_update_event_series(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование мероприятия прервано.")
        return

    db: AsyncSession = await get_db().__anext__()
    result = await db.execute(select(EventSeries))
    event_series = result.scalars().all()

    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{series.name}: {format_date(series.start_date, series.end_date)}",
                                  callback_data=f"update_event_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие для редактирования:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для редактирования.")

    await db.close()


async def select_event_series_to_update(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])
    await state.update_data(series_id=series_id)
    await callback.message.answer("Введите новое название мероприятия:")
    await state.set_state(UpdateEventSeries.waiting_for_name)


async def update_event_series_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование мероприятия прервано.")
        return

    new_name = message.text
    await state.update_data(new_name=new_name)
    await message.answer("Введите новую дату начала мероприятия (в формате ДД.ММ.ГГГГ):")
    await state.set_state(UpdateEventSeries.waiting_for_start_date)


async def update_event_series_start_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование мероприятия прервано.")
        return
    try:
        new_start_date = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(new_start_date=new_start_date)
        await message.answer("Введите новую дату окончания мероприятия (в формате ДД.ММ.ГГГГ):")
        await state.set_state(UpdateEventSeries.waiting_for_end_date)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте снова (ДД.ММ.ГГГГ).")


async def update_event_series_end_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование мероприятия прервано.")
        return
    try:
        new_end_date = datetime.strptime(message.text, "%d.%m.%Y").date()
        data = await state.get_data()
        new_start_date = data.get('new_start_date')
        if new_end_date < new_start_date:
            await message.answer("Дата окончания не может быть раньше даты начала. Попробуйте снова.")
            return

        await state.update_data(new_end_date=new_end_date)
        await message.answer("Введите новое описание мероприятия (или '-' для пропуска):")
        await state.set_state(UpdateEventSeries.waiting_for_description)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте снова (ДД.ММ.ГГГГ).")


async def update_event_series_description(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование мероприятия прервано.")
        return

    new_description = message.text if message.text != "-" else '-'
    await state.update_data(new_description=new_description)
    await message.answer("Загрузите новую фотографию для мероприятия (или '-' для пропуска):")
    await state.set_state(UpdateEventSeries.waiting_for_photo_url)


async def update_event_series_photo_url(message: types.Message, state: FSMContext):
    if text := message.text:
        if text.lower() == "stop":
            await state.clear()
            await message.answer("Редактирование мероприятия прервано.")
            return

    data = await state.get_data()
    series_id = data['series_id']
    new_name = data['new_name']
    new_start_date = data['new_start_date']
    new_end_date = data['new_end_date']
    new_description = data.get('new_description')

    db: AsyncSession = await get_db().__anext__()
    event_series = await db.get(EventSeries, series_id)

    if event_series:
        event_series.name = new_name
        event_series.start_date = new_start_date
        event_series.end_date = new_end_date
        if new_description:
            event_series.description = new_description
        event_series.image_url = message.photo[-1].file_id if message.photo else None
        await db.commit()

        await message.answer(f"Мероприятие '{new_name}' успешно обновлено.")
    else:
        await message.answer("Мероприятие не найдено.")

    await db.close()
    await state.clear()


@admin_only
async def cmd_update_event(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование события прервано.")
        return

    db: AsyncSession = await get_db().__anext__()
    result = await db.execute(select(EventSeries))
    event_series = result.scalars().all()

    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{series.name}: {format_date(series.start_date, series.end_date)}",
                                  callback_data=f"select_event_series_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие, в котором нужно обновить событие:", reply_markup=keyboard)
    else:
        await message.answer("Нет мероприятий для обновления событий.")

    await db.close()


async def select_event_series_for_update_event(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])
    await state.update_data(series_id=series_id)
    db: AsyncSession = await get_db().__anext__()
    result = await db.execute(select(Event).filter(Event.series_id == series_id))
    events = result.scalars().all()

    if events:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{event.event}: {format_date(event.date, event.date)}, {event.time}",
                                  callback_data=f"update_selected_event_{event.id}")]
            for event in events
        ])
        await callback.message.answer("Выберите событие для обновления:", reply_markup=keyboard)
    else:
        await callback.message.answer("Нет событий для обновления.")

    await db.close()


async def select_event_to_update(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[3])
    await state.update_data(event_id=event_id)
    await callback.message.answer("Введите новое название события:")
    await state.set_state(UpdateEvent.waiting_for_event_name)


async def update_event_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование события прервано.")
        return
    new_event_name = message.text
    await state.update_data(new_event_name=new_event_name)
    await message.answer("Введите новую дату события (в формате ДД.ММ.ГГГГ):")
    await state.set_state(UpdateEvent.waiting_for_event_date)


async def update_event_date(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование события прервано.")
        return
    try:
        new_event_date = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(new_event_date=new_event_date)
        await message.answer("Введите новое время события (ЧЧ:ММ - ЧЧ:ММ):")
        await state.set_state(UpdateEvent.waiting_for_event_time)
    except ValueError:
        await message.answer("Неправильный формат даты. Попробуйте снова (ДД.ММ.ГГГГ).")


async def update_event_time(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование события прервано.")
        return

    time_input = message.text.strip()
    try:
        start_time_str, end_time_str = time_input.split('-')
        start_time = datetime.strptime(start_time_str.strip(), "%H:%M").time()
        end_time = datetime.strptime(end_time_str.strip(), "%H:%M").time()

        if start_time >= end_time:
            await message.answer("Время начала не может быть позже или равно времени окончания. Попробуйте снова.")
            return

        await state.update_data(new_event_time=f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")
        await message.answer("Введите новое место проведения события:")
        await state.set_state(UpdateEvent.waiting_for_location)

    except ValueError:
        await message.answer("Неправильный формат времени. Попробуйте снова (ЧЧ:ММ - ЧЧ:ММ).")


async def update_event_location(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование события прервано.")
        return

    new_location = message.text
    await state.update_data(new_location=new_location)
    await message.answer("Введите новое описание события (или '-' для пропуска):")
    await state.set_state(UpdateEvent.waiting_for_description)


async def update_event_description(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование события прервано.")
        return

    new_description = message.text if message.text != "-" else '-'
    await state.update_data(new_description=new_description)
    await message.answer("Введите новых спикеров события (или '-' для пропуска):")
    await state.set_state(UpdateEvent.waiting_for_speakers)


async def update_event_speakers(message: types.Message, state: FSMContext):
    if message.text.lower() == "stop":
        await state.clear()
        await message.answer("Редактирование события прервано.")
        return

    new_speakers = message.text if message.text != "-" else '-'
    await state.update_data(new_speakers=new_speakers)
    await message.answer("Загрузите новую фотографию для события (или '-' для пропуска):")
    await state.set_state(UpdateEvent.waiting_for_photo_url)


async def update_event_photo_url(message: types.Message, state: FSMContext):
    if text := message.text:
        if text.lower() == "stop":
            await state.clear()
            await message.answer("Редактирование события прервано.")
            return

    data = await state.get_data()
    event_id = data['event_id']
    new_event_name = data['new_event_name']
    new_event_date = data['new_event_date']
    new_event_time = data['new_event_time']
    new_location = data['new_location']
    new_speakers = data.get('new_speakers')
    new_description = data.get('new_description')

    db: AsyncSession = await get_db().__anext__()
    event = await db.get(Event, event_id)

    if event:
        event.event = new_event_name
        event.date = new_event_date
        event.time = new_event_time
        event.room = new_location
        if new_speakers:
            event.speakers = new_speakers
        if new_description:
            event.description = new_description
        event.image_url = message.photo[-1].file_id if message.photo else None
        await db.commit()

        await message.answer(f"Событие '{new_event_name}' успешно обновлено.")
    else:
        await message.answer("Событие не найдено.")

    await db.close()
    await state.clear()
