import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import SessionLocal, engine, get_db
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import List, Optional
import models

# Configuración de Seguridad
SECRET_KEY = "taller_pro_auto_honduras_2024"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Esquemas Pydantic
class UserBase(BaseModel):
    username: str
    rol: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    rol: Optional[str] = None

class UserResponse(UserBase):
    id: int
    activo: bool
    class Config:
        from_attributes = True

class ClienteBase(BaseModel):
    nombre: str
    rtn: Optional[str] = None
    telefono: str
    direccion: Optional[str] = None

class ClienteResponse(ClienteBase):
    id: int
    class Config:
        from_attributes = True

class CatalogoBase(BaseModel):
    nombre: str
    precio: float
    tipo: str # 'Producto' o 'Mano de Obra'

class CatalogoResponse(CatalogoBase):
    id: int
    class Config:
        from_attributes = True

class NegocioBase(BaseModel):
    nombre: str
    rtn: str
    telefono: str
    direccion: str
    cai: str
    rango_desde: str
    rango_hasta: str
    fecha_limite: datetime

class NegocioResponse(NegocioBase):
    id: int
    class Config:
        from_attributes = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear usuario admin inicial si no existe
    db = SessionLocal()
    try:
        if not db.query(models.Usuario).filter(models.Usuario.username == "admin").first():
            hashed_pw = pwd_context.hash("admin123")
            admin = models.Usuario(username="admin", password_hash=hashed_pw, rol="admin")
            db.add(admin)
            # Crear también un jefe de pista y cajero para pruebas
            db.add(models.Usuario(username="jefe", password_hash=pwd_context.hash("jefe123"), rol="jefe_pista"))
            db.add(models.Usuario(username="caja", password_hash=pwd_context.hash("caja123"), rol="cajero"))
            db.add(models.Usuario(username="taller", password_hash=pwd_context.hash("taller123"), rol="mecanico"))
            db.commit()

        # Crear configuración de negocio inicial si no existe
        if not db.query(models.NegocioConfig).first():
            config_inicial = models.NegocioConfig(
                nombre="Taller Pro Auto",
                rtn="0000-0000-000000",
                telefono="0000-0000",
                direccion="Dirección del Negocio",
                cai="XXXXXX-XXXXXX-XXXXXX-XXXXXX-XXXXXX-XX",
                rango_desde="000-001-01-00000001",
                rango_hasta="000-001-01-00000999",
                fecha_limite=datetime.utcnow() + timedelta(days=365)
            )
            db.add(config_inicial)
            db.commit()
    finally:
        db.close()
    yield

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Taller Pro Auto - Honduras", lifespan=lifespan)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, usa una lista de dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Usuario).filter(models.Usuario.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Usuario o contraseña incorrectos")
    
    access_token = jwt.encode({"sub": user.username, "rol": user.rol}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer", "rol": user.rol}

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user = db.query(models.Usuario).filter(models.Usuario.username == username).first()
        if user is None: raise HTTPException(status_code=401)
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Sesión inválida")

def check_admin(current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No tiene permisos de administrador")
    return current_user

def check_jefe_or_admin(current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol not in ["admin", "jefe_pista"]:
        raise HTTPException(status_code=403, detail="Permiso denegado: Solo el Administrador o Jefe de Pista pueden registrar clientes")
    return current_user

def check_cajero_or_admin(current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol not in ["admin", "cajero"]:
        raise HTTPException(status_code=403, detail="Permiso denegado: Solo el Administrador o el Cajero pueden anular facturas")
    return current_user

def check_mecanico_or_admin(current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol not in ["admin", "mecanico"]:
        raise HTTPException(status_code=403, detail="Permiso denegado: Solo el Administrador o el Mecánico pueden ver esta pantalla")
    return current_user

@app.get("/")
async def home():
    return FileResponse("index.html")

# --- Gestión de Usuarios (Solo Admin) ---
@app.get("/usuarios/", response_model=List[UserResponse])
def listar_usuarios(db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    return db.query(models.Usuario).all()

@app.post("/usuarios/", response_model=UserResponse)
def crear_usuario(user: UserCreate, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    db_user = db.query(models.Usuario).filter(models.Usuario.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    
    hashed_pw = pwd_context.hash(user.password)
    nuevo_usuario = models.Usuario(username=user.username, password_hash=hashed_pw, rol=user.rol)
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.put("/usuarios/{user_id}", response_model=UserResponse)
def actualizar_usuario(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    db_user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if user_data.username and user_data.username != db_user.username:
        db_existing = db.query(models.Usuario).filter(models.Usuario.username == user_data.username).first()
        if db_existing:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
        db_user.username = user_data.username

    if user_data.password:
        db_user.password_hash = pwd_context.hash(user_data.password)

    if user_data.rol:
        db_user.rol = user_data.rol

    db.commit()
    db.refresh(db_user)
    return db_user

@app.delete("/usuarios/{user_id}")
def eliminar_usuario(user_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    user = db.query(models.Usuario).filter(models.Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="No se puede eliminar el administrador principal")
    
    db.delete(user)
    db.commit()
    return {"message": "Usuario eliminado"}

# --- Gestión de Catálogo (Admin) ---

@app.get("/catalogo/", response_model=List[CatalogoResponse])
def listar_catalogo(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    return db.query(models.ItemCatalogo).all()

@app.post("/catalogo/", response_model=CatalogoResponse)
def crear_item_catalogo(item: CatalogoBase, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    nuevo_item = models.ItemCatalogo(**item.model_dump())
    db.add(nuevo_item)
    db.commit()
    db.refresh(nuevo_item)
    return nuevo_item

@app.delete("/catalogo/{item_id}")
def eliminar_item_catalogo(item_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    item = db.query(models.ItemCatalogo).filter(models.ItemCatalogo.id == item_id).first()
    if not item: raise HTTPException(status_code=404)
    db.delete(item)
    db.commit()
    return {"message": "Item eliminado"}

# --- Gestión de Negocio (Admin) ---
@app.get("/negocio/", response_model=NegocioResponse)
def obtener_negocio(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    return db.query(models.NegocioConfig).first()

@app.put("/negocio/", response_model=NegocioResponse)
def actualizar_negocio(negocio_data: NegocioBase, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    config = db.query(models.NegocioConfig).first()
    for key, value in negocio_data.model_dump().items():
        setattr(config, key, value)
    db.commit()
    db.refresh(config)
    return config

# --- Gestión de Clientes ---

@app.get("/clientes/", response_model=List[ClienteResponse])
def listar_clientes(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    return db.query(models.Cliente).all()

# Endpoint para el Jefe de Pista: Registrar Cliente
@app.post("/clientes/", response_model=ClienteResponse)
def crear_cliente(cliente: ClienteBase, db: Session = Depends(get_db), current_user: models.Usuario = Depends(check_jefe_or_admin)):
    # Normalizar RTN: si es cadena vacía, tratar como None
    rtn_val = cliente.rtn if cliente.rtn and cliente.rtn.strip() != "" else None
    
    if rtn_val:
        db_cliente = db.query(models.Cliente).filter(models.Cliente.rtn == rtn_val).first()
        if db_cliente:
            raise HTTPException(status_code=400, detail="Este RTN ya está registrado en el sistema.")

    nuevo_cliente = models.Cliente(
        nombre=cliente.nombre,
        rtn=rtn_val,
        telefono=cliente.telefono,
        direccion=cliente.direccion
    )
    db.add(nuevo_cliente)
    db.commit()
    db.refresh(nuevo_cliente)
    return nuevo_cliente

@app.put("/clientes/{cliente_id}", response_model=ClienteResponse)
def actualizar_cliente(cliente_id: int, cliente_data: ClienteBase, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Normalizar RTN: tratar cadena vacía como None para evitar errores de unicidad
    rtn_val = cliente_data.rtn if cliente_data.rtn and cliente_data.rtn.strip() != "" else None

    # Verificar unicidad si el RTN está cambiando
    if rtn_val and rtn_val != db_cliente.rtn:
        db_existing = db.query(models.Cliente).filter(models.Cliente.rtn == rtn_val).first()
        if db_existing:
            raise HTTPException(status_code=400, detail="Este RTN ya pertenece a otro cliente")

    db_cliente.nombre = cliente_data.nombre
    db_cliente.rtn = rtn_val
    db_cliente.telefono = cliente_data.telefono
    db_cliente.direccion = cliente_data.direccion
    
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

@app.delete("/clientes/{cliente_id}")
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    db_cliente = db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.delete(db_cliente)
    db.commit()
    return {"message": "Cliente eliminado"}

# Jefe de Pista: Crear Orden de Trabajo
@app.post("/ordenes/")
def crear_orden(
    cliente_id: int, 
    descripcion: str, 
    total: float, 
    tipo: str = "Orden", 
    placa: Optional[str] = None,
    marca: Optional[str] = None,
    modelo: Optional[str] = None,
    anio: Optional[int] = None,
    color: Optional[str] = None,
    requiere_taller: bool = False,
    db: Session = Depends(get_db), 
    current_user: models.Usuario = Depends(get_current_user)
):
    # Buscar o crear vehículo
    vehiculo = None
    if placa:
        vehiculo = db.query(models.Vehiculo).filter(models.Vehiculo.placa == placa).first()
    
    if not vehiculo and marca:
        vehiculo = models.Vehiculo(placa=placa, marca=marca, modelo=modelo, anio=anio, color=color, cliente_id=cliente_id)
        db.add(vehiculo)
        db.flush() # Para obtener el ID

    nueva_orden = models.OrdenTrabajo(
        cliente_id=cliente_id, 
        vehiculo_id=vehiculo.id if vehiculo else None,
        descripcion=descripcion, 
        total=total, 
        tipo=tipo,
        requiere_taller=requiere_taller
    )
    db.add(nueva_orden)
    db.commit()
    return {"message": f"{tipo} creada exitosamente"}

# Cajero: Ver Ordenes Pendientes de Cobro
@app.get("/caja/pendientes")
def listar_pendientes(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Unimos con la tabla de clientes para obtener nombre y RTN para la búsqueda
    query = db.query(models.OrdenTrabajo, models.Cliente).join(
        models.Cliente, models.OrdenTrabajo.cliente_id == models.Cliente.id
    ).filter(models.OrdenTrabajo.estado == "Pendiente").all()
    
    return [{
        "id": o.id,
        "descripcion": o.descripcion,
        "total": o.total,
        "tipo": o.tipo,
        "fecha": o.fecha,
        "cliente_nombre": c.nombre,
        "cliente_rtn": c.rtn or "Consumidor Final",
        "metodo_pago": o.metodo_pago,
        "referencia_pago": o.referencia_pago
    } for o, c in query]

# Cajero: Realizar Cobro
@app.post("/caja/cobrar/{orden_id}")
def cobrar_orden(orden_id: int, metodo_pago: str, referencia_pago: Optional[str] = None, db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not orden: raise HTTPException(status_code=404, detail="Orden no encontrada")
    orden.estado = "Pagada"
    orden.metodo_pago = metodo_pago
    orden.referencia_pago = referencia_pago
    db.commit()
    return {"message": "Cobro realizado con éxito"}

# Admin: Listar Facturas Pagadas
@app.get("/caja/pagadas")
def listar_pagadas(db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    query = db.query(models.OrdenTrabajo, models.Cliente).join(
        models.Cliente, models.OrdenTrabajo.cliente_id == models.Cliente.id
    ).filter(models.OrdenTrabajo.estado == "Pagada").all()
    
    return [{
        "id": o.id,
        "descripcion": o.descripcion,
        "total": o.total,
        "tipo": o.tipo,
        "fecha": o.fecha,
        "cliente_nombre": c.nombre,
        "cliente_rtn": c.rtn or "Consumidor Final",
        "metodo_pago": o.metodo_pago,
        "referencia_pago": o.referencia_pago
    } for o, c in query]

# Admin/Cajero: Anular Factura (Cancelar definitivamente)
@app.post("/caja/anular/{orden_id}")
def anular_factura(orden_id: int, db: Session = Depends(get_db), user: models.Usuario = Depends(check_cajero_or_admin)):
    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not orden: raise HTTPException(status_code=404, detail="Orden no encontrada")
    orden.estado = "Anulada"
    db.commit()
    return {"message": "Factura anulada exitosamente"}

# Pantalla Taller: Marcar trabajo como completado
@app.post("/taller/completar/{orden_id}")
def completar_trabajo(orden_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(check_mecanico_or_admin)):
    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    orden.taller_completado = True
    db.commit()
    return {"message": "Trabajo marcado como completado"}

# Pantalla Taller: Listar Trabajos Pendientes
@app.get("/taller/pendientes")
def listar_taller(db: Session = Depends(get_db), current_user: models.Usuario = Depends(check_mecanico_or_admin)):
    query = db.query(models.OrdenTrabajo, models.Cliente, models.Vehiculo).join(
        models.Cliente, models.OrdenTrabajo.cliente_id == models.Cliente.id
    ).outerjoin(
        models.Vehiculo, models.OrdenTrabajo.vehiculo_id == models.Vehiculo.id
    ).filter(
        models.OrdenTrabajo.taller_completado == False, 
        models.OrdenTrabajo.tipo == "Orden",
        models.OrdenTrabajo.estado != "Anulada",
        models.OrdenTrabajo.requiere_taller == True
    ).all()
    
    return [{
        "id": o.id,
        "tipo_trabajo": o.descripcion.split(';')[0].split('|')[1] if '|' in o.descripcion else o.descripcion,
        "cliente_nombre": c.nombre,
        "vehiculo_marca": v.marca if v else "N/A",
        "vehiculo_modelo": v.modelo if v else "N/A",
        "fecha": o.fecha,
        "estado_pago": o.estado
    } for o, c, v in query]
