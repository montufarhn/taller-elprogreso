from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    rol = Column(String)  # 'admin', 'cajero', 'jefe_pista'
    activo = Column(Boolean, default=True)

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    rtn = Column(String, unique=True, nullable=True)
    telefono = Column(String)
    direccion = Column(String, nullable=True)
    vehiculos = relationship("Vehiculo", back_populates="dueno")

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String, unique=True, index=True)
    marca = Column(String)
    modelo = Column(String)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    dueno = relationship("Cliente", back_populates="vehiculos")

class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"))
    estado = Column(String, default="Pendiente") # Pendiente, Aceptada
    total = Column(Float, default=0.0)
    fecha = Column(DateTime, default=datetime.utcnow)

class OrdenTrabajo(Base):
    __tablename__ = "ordenes_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"))
    descripcion = Column(String)
    total = Column(Float, default=0.0)
    tipo = Column(String, default="Orden") # 'Orden' o 'Cotizacion'
    estado = Column(String, default="Pendiente") # 'Pendiente', 'Pagada'
    metodo_pago = Column(String, nullable=True)
    referencia_pago = Column(String, nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)

class ItemCatalogo(Base):
    __tablename__ = "catalogo"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    tipo = Column(String) # 'Producto' o 'Mano de Obra'

class NegocioConfig(Base):
    __tablename__ = "negocio_config"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    rtn = Column(String)
    telefono = Column(String)
    direccion = Column(String)
    cai = Column(String)
    rango_desde = Column(String)
    rango_hasta = Column(String)
    fecha_limite = Column(DateTime)
