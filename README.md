# MGSymposiumBot

# Бот для МГСУ

def register_update_cmd(dp: Dispatcher):
    dp.message.register(cmd_update_event_series, Command(
        commands=["update"]))
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