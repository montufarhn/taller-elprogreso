import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy import event
import models # Import your models
from database import get_db_path # Re-use the path logic

# --- Configuration ---
# Supabase (PostgreSQL) connection string - MUST be set as an environment variable
SUPABASE_DATABASE_URL = os.environ.get("DATABASE_URL")

# Limpiar posibles espacios en blanco al inicio o final
if SUPABASE_DATABASE_URL:
    SUPABASE_DATABASE_URL = SUPABASE_DATABASE_URL.strip()

# Ruta local para la base de datos de destino
SQLITE_DB_PATH = os.path.join(get_db_path(), 'taller.db')
SQLITE_DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"

# Fix for SQLAlchemy: Render and other providers use "postgres://" but require "postgresql://"
if SUPABASE_DATABASE_URL and SUPABASE_DATABASE_URL.startswith("postgres://"):
    SUPABASE_DATABASE_URL = SUPABASE_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not SUPABASE_DATABASE_URL:
    print("\n[!] ERROR: No se encontró la variable DATABASE_URL.")
    print("Asegúrate de ejecutar: export DATABASE_URL='tu_url_aqui' antes del script.")
    sys.exit(1)

print(f"Iniciando migración de datos desde: {SUPABASE_DATABASE_URL}")
print(f"Hacia la base de datos SQLite local: {SQLITE_DATABASE_URL}")

# --- SQLAlchemy Engines and Sessions ---

# Supabase (Source) Engine
supabase_engine = create_engine(SUPABASE_DATABASE_URL)
SupabaseSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=supabase_engine)

# SQLite (Destination) Engine
sqlite_engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})

@event.listens_for(sqlite_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SqliteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

def migrate_data():
    # 1. Drop existing tables in SQLite (for a clean start)
    print("\n[SQLite] Eliminando tablas existentes (si las hay)...")
    models.Base.metadata.drop_all(bind=sqlite_engine)
    print("[SQLite] Tablas eliminadas.")

    # 2. Create tables in SQLite
    print("[SQLite] Creando estructura de tablas...")
    models.Base.metadata.create_all(bind=sqlite_engine)
    print("[SQLite] Estructura de tablas creada.")

    supabase_session = SupabaseSessionLocal()
    sqlite_session = SqliteSessionLocal()

    try:
        # Orden de migración para respetar Foreign Keys
        tables_to_migrate = [
            models.Usuario,
            models.Cliente,
            models.ItemCatalogo,
            models.Egreso,
            models.NegocioConfig,
            models.NotaVersion,
            models.Vehiculo, # Depends on Cliente
            models.Cotizacion, # Depends on Vehiculo
            models.OrdenTrabajo, # Depends on Cliente, Vehiculo, Usuario
        ]

        for Model in tables_to_migrate:
            print(f"\nMigrando datos para la tabla: {Model.__tablename__}")
            
            supabase_records = supabase_session.query(Model).all()
            
            if not supabase_records:
                print(f"No hay registros en {Model.__tablename__} en Supabase. Saltando.")
                continue

            new_records = []
            for record in supabase_records:
                new_record_data = {col.name: getattr(record, col.name) for col in Model.__table__.columns}
                new_records.append(Model(**new_record_data))
            
            sqlite_session.bulk_save_objects(new_records)
            sqlite_session.commit()
            print(f"Migrados {len(new_records)} registros a {Model.__tablename__}.")

        print("\n¡Migración de datos completada exitosamente!")

    except IntegrityError as e:
        sqlite_session.rollback()
        print(f"Error de integridad de datos durante la migración: {e}")
        print("Asegúrese de que el orden de migración de tablas respete las claves foráneas.")
        print(f"Detalle: {e.orig}")
    except Exception as e:
        sqlite_session.rollback()
        print(f"Ocurrió un error inesperado durante la migración: {e}")
    finally:
        supabase_session.close()
        sqlite_session.close()

if __name__ == "__main__":
    migrate_data()
