# read.py
import os
from dotenv import load_dotenv
from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from sqlalchemy.future import select
from models import Event, EventSeries, get_db
from utils import is_url_valid, format_date

load_dotenv()
logo = os.getenv('MGSU_DEFAULT_LOGO')


async def cmd_start(message: types.Message):
    async for db in get_db():
        try:
            result = await db.execute(select(EventSeries))
            event_series = result.scalars().all()
        except Exception as e:
            await message.answer("Ошибка при получении списка мероприятий.")
            print(f"Error fetching event series: {e}")
            return
        finally:
            await db.close()  # Явно закрываем соединение после завершения работы

        if event_series:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{series.name}: {format_date(series.start_date, series.end_date)}",
                    callback_data=f"series_{series.id}")]
                for series in sorted(event_series, key=lambda s: s.start_date)
            ])
            if is_url_valid(logo):
                await message.answer_photo(photo=logo, caption="Список мероприятий: ", reply_markup=keyboard)
            else:
                await message.answer("Список мероприятий: ", reply_markup=keyboard)
        else:
            await message.answer("Нет запланированных мероприятий.")


async def show_events(callback: CallbackQuery):
    series_id = int(callback.data.split("_")[1])
    async for db in get_db():
        try:
            result = await db.execute(select(Event).filter(Event.series_id == series_id).order_by(Event.date))
            events = result.scalars().all()

            result_series = await db.execute(select(EventSeries).filter(EventSeries.id == series_id))
            events_series = result_series.scalars().first()
        except Exception as e:
            await callback.message.answer("Ошибка при получении событий.")
            print(f"Error fetching events: {e}")
            return
        finally:
            await db.close()

        if events:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{event.event}: {format_date(event.date, event.date)}, {event.time}",
                    callback_data=f"event_{event.id}")]
                for event in events
            ])
            series_details = (
                f"<b>{events_series.name}</b>"
                f"\nДата начала: {events_series.start_date.strftime('%d.%m.%Y')}"
                f"\nДата окончания: {events_series.end_date.strftime('%d.%m.%Y')}"
            )
            if events_series.description and events_series.description != "-":
                series_details += f"\nОписание: {events_series.description}"

            if events_series.image_url:
                await callback.message.answer_photo(
                    photo=events_series.image_url,
                    caption=series_details,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
            else:
                await callback.message.answer(
                    text=series_details,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
        else:
            await callback.message.answer("Нет событий в этом мероприятии.")


async def show_event_details(callback: CallbackQuery):
    event_id = int(callback.data.split("_")[1])
    async for db in get_db():
        try:
            result = await db.execute(select(Event).filter(Event.id == event_id))
            event = result.scalars().first()
        except Exception as e:
            await callback.message.answer("Ошибка при получении деталей события.")
            print(f"Error fetching event details: {e}")
            return
        finally:
            await db.close()

        if event:
            details = (
                f"<b>Мероприятие:</b> {event.event}\n"
                f"<b>Дата:</b> {event.date.strftime('%d.%m.%Y')}\n"
                f"<b>Время:</b> {event.time}\n"
                f"<b>Место:</b> {event.room}\n"
            )
            if event.speakers and event.speakers != "-":
                details += f"<b>Спикеры:</b> {event.speakers}\n"
            if event.description and event.description != "-":
                details += f"<b>Описание:</b> {event.description}\n"

            if event.image_url:
                await callback.message.answer_photo(
                    photo=event.image_url,
                    caption=details,
                    parse_mode='HTML'
                )
            else:
                await callback.message.answer(details, parse_mode='HTML')
        else:
            await callback.message.answer("Событие не найдено.")


def register_read_cmd(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.callback_query.register(
        show_events, lambda c: c.data.startswith("series_"))
    dp.callback_query.register(
        show_event_details, lambda c: c.data.startswith("event_"))
