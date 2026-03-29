from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Si existe la variable de entorno DATABASE_URL (en la nube), la usa.
# Si no, usa SQLite localmente.
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./taller.db")

# SQLite necesita check_same_thread, pero PostgreSQL no.
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()