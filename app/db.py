# app/db.py

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from sqlmodel import SQLModel, Session, create_engine
from flask import Flask, current_app



def init_db(flask_app: Flask, database_url: str) -> None:
    """Инициализация БД для Flask-приложения.

    - создаём engine один раз при старте приложения
    - сохраняем engine в app.config, чтобы им пользовались роуты
    - создаём таблицы, если их ещё нет (для учебного проекта вместо миграций)
    """
    # ВАЖНО: импортируем модели ДО create_all, чтобы таблицы попали в SQLModel.metadata.
    # Используем `from app import models`, чтобы не затереть переменную flask_app.
    from app import models  # noqa: F401

    engine = create_engine(database_url)
    flask_app.config["DB_ENGINE"] = engine

    # Создаём таблицы, если их ещё нет (идемпотентно)
    SQLModel.metadata.create_all(engine)


def get_engine():
    """Достаём engine из текущего Flask-приложения."""
    return current_app.config["DB_ENGINE"]


@contextmanager
def get_session() -> Iterator[Session]:
    """Контекстный менеджер для сессии БД.

    Использование:
        with get_session() as session:
            ...
    """
    engine = get_engine()
    with Session(engine) as session:
        yield session