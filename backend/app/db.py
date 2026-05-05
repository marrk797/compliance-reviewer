"""SQLite engine, session, and sqlite-vec setup.

We use ``pysqlite3-binary`` as the driver because the system ``sqlite3`` on
many Linux distros is built without ``--enable-loadable-sqlite-extensions``,
which sqlite-vec needs.
"""
from __future__ import annotations

import sys
from collections.abc import Iterator

# Prefer pysqlite3 so loadable extensions work everywhere.
import pysqlite3 as _sqlite3  # noqa: F401  (must be imported before sqlalchemy)
import sqlite_vec
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# Make `import sqlite3` resolve to pysqlite3 for SQLAlchemy's pysqlite dialect.
sys.modules["sqlite3"] = sys.modules["pysqlite3"]
sys.modules["sqlite3.dbapi2"] = sys.modules["pysqlite3.dbapi2"]


def _build_url() -> str:
    return f"sqlite:///{settings.database_path}"


engine = create_engine(_build_url(), future=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@event.listens_for(engine, "connect")
def _on_connect(dbapi_connection, _connection_record) -> None:
    """Load sqlite-vec into every SQLite connection."""
    dbapi_connection.enable_load_extension(True)
    sqlite_vec.load(dbapi_connection)
    dbapi_connection.enable_load_extension(False)
    dbapi_connection.execute("PRAGMA foreign_keys = ON")
    dbapi_connection.execute("PRAGMA journal_mode = WAL")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and the vec0 virtual table on app startup.

    SQLite is permissive about repeat ``CREATE TABLE IF NOT EXISTS``, so this
    is safe to call on every boot.
    """
    # Importing the models package registers them with the metadata.
    from app.models import register_models

    register_models()
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS company_chunks_vec USING vec0(
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT PARTITION KEY,
                embedding float[{settings.embedding_dim}]
            )
            """
        )
