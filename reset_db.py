import models
from database import engine, SessionLocal
from main import lifespan
import asyncio
from fastapi import FastAPI

def reset_database():
    print("⚠️  Iniciando reset de base de datos en Supabase...")
    
    # 1. Eliminar todas las tablas existentes
    models.Base.metadata.drop_all(bind=engine)
    print("✅ Todas las tablas han sido eliminadas.")
    
    # 2. Recrear las tablas con la estructura limpia
    models.Base.metadata.create_all(bind=engine)
    print("✅ Estructura de tablas recreada exitosamente.")
    print("\n💡 Nota: Los usuarios iniciales se crearán automáticamente al iniciar la app en Render.")

if __name__ == "__main__":
    reset_database()