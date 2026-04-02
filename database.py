from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import event
import os
import sys # Import sys for PyInstaller path handling

# Determine the base path for the database file
def get_db_path():
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle, use the directory of the executable
        return os.path.dirname(sys.executable)
    else:
        # Running as a script
        return os.path.dirname(os.path.abspath(__file__))

DB_BASE_PATH = get_db_path()

# Si existe la variable de entorno DATABASE_URL (en la nube), la usa.
# Si no, usa SQLite localmente.
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(DB_BASE_PATH, 'taller.db')}")

# Fix para SQLAlchemy: Render y otros proveedores usan "postgres://" pero se requiere "postgresql://"
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite necesita check_same_thread, pero PostgreSQL no.
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

# Esta parte es CRUCIAL para que SQLite respete los CASCADE y SET NULL
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()