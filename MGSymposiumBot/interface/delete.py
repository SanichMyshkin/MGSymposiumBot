from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup


from sqlalchemy.orm import Session

from models import Event, EventSeries, get_db
from utils import admin_only


def register_delete_cmd(dp: Dispatcher):
    dp.message.register(cmd_delete_event_series, Command(commands=["delete"]))
    dp.callback_query.register(
        delete_series, lambda c: c.data.startswith("delete_series_"))
    dp.callback_query.register(
        confirm_delete_series, lambda c: c.data == "confirm_delete_series")
    dp.callback_query.register(
        cancel_delete, lambda c: c.data == "cancel_delete")

    dp.message.register(cmd_delete_event, Command(commands=["delete_event"]))
    dp.callback_query.register(select_event_series_to_delete_event,
                               lambda c: c.data.startswith("delete_event_series_"))
    dp.callback_query.register(
        delete_selected_event, lambda c: c.data.startswith("delete_selected_event_"))
    dp.callback_query.register(
        confirm_delete_event, lambda c: c.data == "confirm_delete_event")
    dp.callback_query.register(
        cancel_delete_event, lambda c: c.data == "cancel_delete_event")


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


async def delete_series(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[2])
    await state.update_data(series_id=series_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да", callback_data="confirm_delete_series")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel_delete")]
    ])
    await callback.message.answer("Удалить мероприятие и все связанные события?", reply_markup=keyboard)


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


async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление отменено.")
    await state.clear()


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


async def select_event_series_to_delete_event(callback: CallbackQuery, state: FSMContext):
    series_id = int(callback.data.split("_")[3])
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


async def delete_selected_event(callback: CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[3])
    await state.update_data(event_id=event_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Да", callback_data="confirm_delete_event")],
        [InlineKeyboardButton(text="Нет", callback_data="cancel_delete_event")]
    ])
    await callback.message.answer("Вы уверены, что хотите удалить это событие?", reply_markup=keyboard)


async def confirm_delete_event(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    event_id = data['event_id']

    db: Session = next(get_db())
    event = db.query(Event).filter(Event.id == event_id).first()

    if event:
        db.delete(event)
        db.commit()
        db.close()
        await callback.message.answer(f"Событие '{event.event}' успешно удалено.")
    else:
        await callback.message.answer("Событие не найдено.")
    await state.clear()


async def cancel_delete_event(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Удаление события отменено.")
    await state.clear()
