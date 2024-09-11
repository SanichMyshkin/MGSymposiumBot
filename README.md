# MGSymposiumBot


3. упаковать самого бота в докер

# ВАЖНЫЕ
1. crud -  Сделано уже добавление чтение удаление(кривое но работает) - готовы
   
    Отлавливать сотальные сообщения
    разбить на разные файлы
    Описание у мероприятий и фотографии отсуствуют, надо что-то сделать с этим
    Внести все в один пост (фото+ текст)
    Навести порядок с фоматами вывода, а то грустно все
3. вынести админку
4. ВАЛИДАЦИЯ И ТЕСТЫ ЖЕЛАТЕЛЬНО

5. Проверять ссылку на аботспособность, если нет, то просто не выводить фото, а то бот ругается на плохи сыылки
6. Добавиь хелп 


from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.filters.state import StateFilter
import logging
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import Event, EventSeries, init_db, get_db

# Загрузка переменных окружения
load_dotenv()

bot = Bot(token=os.getenv("BOT_TOKEN"))
dispatcher = Dispatcher()

# Логирование
logging.basicConfig(level=logging.INFO)

# Состояния для добавления мероприятий и событий
class AddEventSeries(StatesGroup):
    waiting_for_name = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()

class AddEvent(StatesGroup):
    waiting_for_event_series = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_room = State()
    waiting_for_speakers = State()

# Команда /start
@dispatcher.message(Command(commands=["start"]))
async def cmd_start(message: Message):
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

# Обработка нажатия на кнопку мероприятия
@dispatcher.callback_query(lambda callback_query: callback_query.data.startswith("series_"))
async def show_event_series(callback_query: CallbackQuery):
    series_id = int(callback_query.data.split("_")[1])

    db: Session = next(get_db())
    series = db.query(EventSeries).filter(EventSeries.id == series_id).first()

    if series:
        events = series.events
        if events:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"Событие: {event.event} ({event.date}, {event.time})",
                    callback_data=f"event_{event.id}")]
                for event in events
            ])
            await callback_query.message.answer(f"Мероприятие: {series.name}\nСписок событий:", reply_markup=keyboard)
        else:
            await callback_query.message.answer("В этом мероприятии пока нет событий.")
    else:
        await callback_query.message.answer("Мероприятие не найдено.")

# Команда для добавления мероприятия
@dispatcher.message(Command(commands=["addeventseries"]))
async def cmd_addeventseries(message: Message, state: FSMContext):
    await message.answer("Введите название мероприятия или нажмите отмена для выхода.")
    await state.set_state(AddEventSeries.waiting_for_name)

# Обработка отмены
@dispatcher.message(F.text.lower() == "отмена", StateFilter("*"))
async def cancel_action(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.")

# Обработка добавления мероприятия
@dispatcher.message(state=AddEventSeries.waiting_for_name)
async def process_event_series_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите дату начала мероприятия (в формате ГГГГ-ММ-ДД).")
    await state.set_state(AddEventSeries.waiting_for_start_date)

@dispatcher.message(state=AddEventSeries.waiting_for_start_date)
async def process_event_series_start_date(message: Message, state: FSMContext):
    await state.update_data(start_date=message.text)
    await message.answer("Введите дату окончания мероприятия (в формате ГГГГ-ММ-ДД).")
    await state.set_state(AddEventSeries.waiting_for_end_date)

@dispatcher.message(state=AddEventSeries.waiting_for_end_date)
async def process_event_series_end_date(message: Message, state: FSMContext):
    user_data = await state.get_data()
    db: Session = next(get_db())
    
    new_series = EventSeries(
        name=user_data['name'],
        start_date=user_data['start_date'],
        end_date=message.text
    )
    
    db.add(new_series)
    db.commit()

    await state.clear()
    await message.answer("Мероприятие успешно добавлено!")

# Команда для добавления события
@dispatcher.message(Command(commands=["addevent"]))
async def cmd_addevent(message: Message, state: FSMContext):
    db: Session = next(get_db())
    event_series = db.query(EventSeries).all()

    if event_series:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{series.name} ({series.start_date} - {series.end_date})",
                callback_data=f"addeventseries_{series.id}")]
            for series in event_series
        ])
        await message.answer("Выберите мероприятие, к которому хотите добавить событие:", reply_markup=keyboard)
        await state.set_state(AddEvent.waiting_for_event_series)
    else:
        await message.answer("Сначала добавьте хотя бы одно мероприятие с помощью команды /addeventseries.")

# Обработка выбора мероприятия для добавления события
@dispatcher.callback_query(lambda callback_query: callback_query.data.startswith("addeventseries_"), state=AddEvent.waiting_for_event_series)
async def process_event_series_selection(callback_query: CallbackQuery, state: FSMContext):
    series_id = int(callback_query.data.split("_")[1])
    await state.update_data(series_id=series_id)
    await callback_query.message.answer("Введите дату события (в формате ГГГГ-ММ-ДД).")
    await state.set_state(AddEvent.waiting_for_date)

@dispatcher.message(state=AddEvent.waiting_for_date)
async def process_event_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.answer("Введите время события (в формате ЧЧ:ММ).")
    await state.set_state(AddEvent.waiting_for_time)

@dispatcher.message(state=AddEvent.waiting_for_time)
async def process_event_time(message: Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer("Введите комнату, где будет проходить событие.")
    await state.set_state(AddEvent.waiting_for_room)

@dispatcher.message(state=AddEvent.waiting_for_room)
async def process_event_room(message: Message, state: FSMContext):
    await state.update_data(room=message.text)
    await message.answer("Введите список выступающих (через запятую).")
    await state.set_state(AddEvent.waiting_for_speakers)

@dispatcher.message(state=AddEvent.waiting_for_speakers)
async def process_event_speakers(message: Message, state: FSMContext):
    user_data = await state.get_data()
    db: Session = next(get_db())

    new_event = Event(
        series_id=user_data['series_id'],
        date=user_data['date'],
        time=user_data['time'],
        room=user_data['room'],
        speakers=message.text,
        event="Событие"  # Добавьте реальное название события, если нужно
    )
    
    db.add(new_event)
    db.commit()

    await state.clear()
    await message.answer("Событие успешно добавлено!")

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