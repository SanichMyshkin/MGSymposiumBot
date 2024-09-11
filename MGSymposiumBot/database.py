from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Time
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
    events = relationship("Event", back_populates="series")


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(Integer, ForeignKey('event_series.id'), nullable=False)
    date = Column(Date, nullable=False)
    time = Column(Time, nullable=False)
    event = Column(String, nullable=False)
    room = Column(String, nullable=False)
    speakers = Column(String)
    series = relationship("EventSeries", back_populates="events")


# Создание движка базы данных
engine = create_engine(DATABASE_URL)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
