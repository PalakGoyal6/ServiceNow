from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

# If relative path for sqlite, ensure connect_args check_same_thread=False
is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Enable SQLite PRAGMAs on every connection
if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
