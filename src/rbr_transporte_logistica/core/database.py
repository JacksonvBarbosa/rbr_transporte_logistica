from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/frete_system"


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def create_db_engine(database_url: str | None = None):
    url = database_url or get_database_url()
    return create_engine(url, echo=False, future=True, connect_args=_connect_args(url))


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def create_all() -> None:
    from rbr_transporte_logistica.core import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@contextmanager
def db_session(
    session_factory: sessionmaker[Session] = SessionLocal,
) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
