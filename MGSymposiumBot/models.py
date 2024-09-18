from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()


class EventSeries(Base):
    __tablename__ = 'event_series'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    description = Column(String)  # Описание серии мероприятий
    image_url = Column(String, nullable=True)
    events = relationship("Event", back_populates="series")


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey('event_series.id'), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(String, nullable=False)
    event = Column(String, nullable=False)
    room = Column(String, nullable=False)
    speakers = Column(String)
    description = Column(String)
    image_url = Column(String, nullable=True)
    series = relationship("EventSeries", back_populates="events")


engine = create_async_engine(DATABASE_URL, echo=True)

# Создание асинхронной сессии
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
