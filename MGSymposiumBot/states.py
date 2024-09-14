from aiogram.fsm.state import State, StatesGroup


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
