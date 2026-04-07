from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    rol = Column(String)  # 'admin', 'cajero', 'jefe_pista'
    activo = Column(Boolean, default=True)
    ordenes_asignadas = relationship("OrdenTrabajo", backref="mecanico", passive_deletes=True)

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    rtn = Column(String, unique=True, nullable=True)
    dni = Column(String, nullable=True)
    telefono = Column(String)
    direccion = Column(String, nullable=True)
    vehiculos = relationship("Vehiculo", back_populates="dueno", cascade="all, delete-orphan")
    ordenes = relationship("OrdenTrabajo", back_populates="cliente")

class Vehiculo(Base):
    __tablename__ = "vehiculos"
    id = Column(Integer, primary_key=True, index=True)
    placa = Column(String, unique=True, index=True)
    marca = Column(String)
    modelo = Column(String)
    anio = Column(Integer, nullable=True)
    color = Column(String, nullable=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"))
    dueno = relationship("Cliente", back_populates="vehiculos")

class Cotizacion(Base):
    __tablename__ = "cotizaciones"
    id = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id"))
    estado = Column(String, default="Pendiente") # Pendiente, Aceptada
    total = Column(Float, default=0.0)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class OrdenTrabajo(Base):
    __tablename__ = "ordenes_trabajo"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"), nullable=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id", ondelete="SET NULL"), nullable=True)
    descripcion = Column(String)
    total = Column(Float, default=0.0)
    tipo = Column(String, default="Orden") # 'Orden' o 'Cotizacion'
    factura_nombre = Column(String)
    factura_rtn = Column(String, nullable=True)
    factura_dni = Column(String, nullable=True)
    estado = Column(String, default="Pendiente") # 'Pendiente', 'Pagada'
    metodo_pago = Column(String, nullable=True)
    referencia_pago = Column(String, nullable=True)
    comprobante_pago = Column(String, nullable=True) # Almacena imagen en Base64
    taller_completado = Column(Boolean, default=False)
    requiere_taller = Column(Boolean, default=False)
    mecanico_id = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    inicio_trabajo = Column(DateTime, nullable=True)
    fin_trabajo = Column(DateTime, nullable=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    cliente = relationship("Cliente", back_populates="ordenes")

class ItemCatalogo(Base):
    __tablename__ = "catalogo"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    tipo = Column(String) # 'Producto' o 'Mano de Obra'
    existencia = Column(Integer, default=0)

class Egreso(Base):
    __tablename__ = "egresos"
    id = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String)
    monto = Column(Float, default=0.0)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))

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
    numero_inicio_factura = Column(Integer, default=1)
    logo = Column(String, nullable=True)

class NotaVersion(Base):
    __tablename__ = "notas_version"
    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    titulo = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    version = Column(String, nullable=False)
