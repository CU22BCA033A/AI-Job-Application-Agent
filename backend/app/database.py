from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

is_sqlite = settings.database_url.startswith("sqlite")

# Serverless functions are short-lived processes, so a warm connection pool
# doesn't carry over between invocations the way it would on a long-running
# server — NullPool (open a fresh connection per request) plus pre-ping
# avoids handing out connections a previous cold start already dropped.
engine_kwargs: dict = {"connect_args": {"check_same_thread": False}} if is_sqlite else {
    "poolclass": NullPool,
    "pool_pre_ping": True,
}
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401  (ensure models are registered on Base)

    Base.metadata.create_all(bind=engine)
