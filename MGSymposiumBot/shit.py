from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
import asyncio
from models import Event, EventSeries  # Убедитесь, что модели импортированы корректно

# URL вашей базы данных
DATABASE_URL = "postgresql+asyncpg://MGSU:yStNUiyChuRn9C0ZiaP2HgsQQ@postgres:5432/symposium"

# Настраиваем движок для асинхронной работы с базой данных
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаём фабрику сессий для взаимодействия с базой данных
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Вставляем данные для event_series и events
async def populate_data():
    async with AsyncSessionLocal() as session:  # Здесь мы правильно инициализируем сессию
        # Проверяем, существует ли запись для указанной серии мероприятий
        result = await session.execute(
            select(EventSeries).where(EventSeries.name == 'Международный научно-практический симпозиум «Будущее строительной отрасли: вызовы и перспективы развития»')
        )
        series = result.scalars().first()

        # Если запись не найдена, создаем её
        if not series:
            series = EventSeries(
                id=2,
                name='Международный научно-практический симпозиум «Будущее строительной отрасли: вызовы и перспективы развития»',
                start_date='2024-09-16',
                end_date='2024-09-20',
                description='Описание серии мероприятий',
                image_url=None
            )
            session.add(series)
            await session.commit()

        # Данные для событий
        events_data = [
            {'series_id': 2, 'date': '2024-09-16', 'time': '11:00 - 12:00', 'event': 'Пленарное заседание по модульному строительству с МШХ',
                'room': 'Актовый зал', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '09:00 - 10:00', 'event': 'РЕГИСТРАЦИЯ',
                'room': 'Фойе актового зала', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '10:00 - 11:45', 'event': 'Международный конгресс молодых архитекторов и дизайнеров',
                'room': 'КПА', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '10:00 - 18:00', 'event': 'Стратегическая сессия «Кампусы мирового уровня»',
                'room': 'Зал ученого совета', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '10:00 - 13:00', 'event': 'Круглый стол «Социально-гуманитарные аспекты строительной отрасли»',
                'room': 'НТБ 47', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '10:00 - 11:30', 'event': 'Мастер-класс от академика РААСН',
                'room': 'НТБ 59', 'speakers': 'Каприелов Семён Суренович', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '11:30 - 13:00', 'event': 'Мастер-класс от академика РААСН',
                'room': 'НТБ 59', 'speakers': 'Ерофеев Владимир Трофимович', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '11:00 - 13:00', 'event': 'Стратегическая сессия «Кадры для ЖКХ»',
                'room': 'Коворкинг', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '14:00 - 18:00', 'event': 'Стратегическая сессия «Молодые ученые»',
                'room': 'Коворкинг', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '14:00 - 18:00', 'event': 'Круглый стол «Организационно-технологические решения при изысканиях, проектировании и строительстве»',
                'room': '9 студия', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '14:00 - 18:00', 'event': 'Круглый стол «Биосфера и город»',
                'room': '10 студия', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '14:00 - 18:00', 'event': 'Круглый стол «Строительная механика - взгляд в будущее»',
                'room': '405 УЛК', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '14:00 - 18:00', 'event': 'Круглый стол «Сейсмостойкое строительство»',
                'room': 'НТБ 47', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '14:00 - 18:00', 'event': 'Круглый стол «Современные вызовы и приоритеты развития методов расчета строительных конструкций»',
                'room': 'НТБ 59', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '15:00 - 17:00', 'event': 'Круглый стол «Индустриальные методы строительства АЭС»',
                'room': '420 УЛК', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 7, 'date': '2024-09-17', 'time': '16:00 - 18:00', 'event': 'Круглый стол «Роль вовлеченности и мотивации к изучению иностранных языков для профессиональных целей»',
                'room': '624 КМК', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 8, 'date': '2024-09-18', 'time': '09:00 - 10:00', 'event': 'РЕГИСТРАЦИЯ',
                'room': 'Фойе актового зала', 'speakers': '-', 'description': None, 'image_url': None},
            {'series_id': 8, 'date': '2024-09-18', 'time': '10:00 - 18:00', 'event': 'Международная конференция «Механика грунтов и геотехника в высотном и подземном строительстве»',
                'room': 'Зал ученого совета', 'speakers': '-', 'description': None, 'image_url': None},
            # Добавьте остальные события сюда аналогичным образом
        ]


        # Вставляем данные для событий
        for event_data in events_data:
            event = Event(**event_data)
            session.add(event)

        # Коммитим после добавления всех событий
        await session.commit()

# Функция запуска заполнения базы данных
async def main():
    await populate_data()  # Заполняем базу данных

if __name__ == '__main__':
    asyncio.run(main())