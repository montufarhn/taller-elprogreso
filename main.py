import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from database import SessionLocal, engine, get_db
from datetime import datetime, timedelta, timezone
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
    identidad: Optional[str] = None
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
    existencia: int = 0

class CatalogoResponse(CatalogoBase):
    id: int
    class Config:
        from_attributes = True

class EgresoBase(BaseModel):
    descripcion: str
    monto: float

class EgresoResponse(EgresoBase):
    id: int
    fecha: datetime
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
    logo: Optional[str] = None

class NegocioResponse(NegocioBase):
    id: int
    class Config:
        from_attributes = True

class FacturacionUpdate(BaseModel):
    nombre: str
    identidad: Optional[str] = None

class CobroRequest(BaseModel):
    metodo_pago: str
    referencia_pago: Optional[str] = None
    comprobante: Optional[str] = None

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
                fecha_limite=datetime.now(timezone.utc) + timedelta(days=365)
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
    return {"access_token": access_token, "token_type": "bearer", "rol": user.rol, "user_id": user.id}

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
        raise HTTPException(status_code=403, detail="Permiso denegado: Acceso restringido a Administrador o Cajero")
    return current_user

def check_mecanico_or_admin(current_user: models.Usuario = Depends(get_current_user)):
    if current_user.rol not in ["admin", "mecanico"]:
        raise HTTPException(status_code=403, detail="Permiso denegado: Solo el Administrador o el Mecánico pueden ver esta pantalla")
    return current_user

def procesar_identidad(identidad_str: Optional[str]):
    if not identidad_str:
        return None, None
    digits = "".join(filter(str.isdigit, identidad_str))
    if len(digits) > 13:
        return identidad_str, None
    return None, identidad_str

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

@app.get("/inventario/", response_model=List[CatalogoResponse])
def listar_inventario(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    return db.query(models.ItemCatalogo).all()

@app.post("/inventario/", response_model=CatalogoResponse)
def crear_item_inventario(item: CatalogoBase, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    nuevo_item = models.ItemCatalogo(**item.model_dump())
    db.add(nuevo_item)
    db.commit()
    db.refresh(nuevo_item)
    return nuevo_item

@app.put("/inventario/{item_id}", response_model=CatalogoResponse)
def actualizar_item_catalogo(item_id: int, item_data: CatalogoBase, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    item = db.query(models.ItemCatalogo).filter(models.ItemCatalogo.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    item.nombre = item_data.nombre
    item.precio = item_data.precio
    item.tipo = item_data.tipo
    item.existencia = item_data.existencia
    db.commit()
    db.refresh(item)
    return item

@app.post("/inventario/comprar")
def comprar_inventario(item_id: int, cantidad: int, costo_total: float, db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    item = db.query(models.ItemCatalogo).filter(models.ItemCatalogo.id == item_id).first()
    if not item: raise HTTPException(status_code=404)
    
    # Aumentar stock
    item.existencia += cantidad
    
    # Registrar Egreso
    nuevo_egreso = models.Egreso(descripcion=f"Compra de Inventario: {cantidad}x {item.nombre}", monto=costo_total)
    db.add(nuevo_egreso)
    
    db.commit()
    return {"message": "Inventario actualizado y egreso registrado"}

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
    if not config:
        config = models.NegocioConfig()
        db.add(config)
    
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
    rtn, dni = procesar_identidad(cliente.identidad)
    
    if rtn and db.query(models.Cliente).filter(models.Cliente.rtn == rtn).first():
        raise HTTPException(status_code=400, detail="Este RTN ya está registrado.")

    nuevo_cliente = models.Cliente(
        nombre=cliente.nombre,
        rtn=rtn,
        dni=dni,
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
    
    rtn, dni = procesar_identidad(cliente_data.identidad)

    db_cliente.nombre = cliente_data.nombre
    db_cliente.rtn = rtn
    db_cliente.dni = dni
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
    factura_nombre: str,
    factura_identidad: Optional[str] = None,
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
    
    rtn, dni = procesar_identidad(factura_identidad)

    nueva_orden = models.OrdenTrabajo(
        cliente_id=cliente_id, 
        vehiculo_id=vehiculo.id if vehiculo else None,
        factura_nombre=factura_nombre,
        factura_rtn=rtn,
        factura_dni=dni,
        descripcion=descripcion, 
        total=total, 
        tipo=tipo,
        requiere_taller=requiere_taller
    )
    db.add(nueva_orden)
    db.commit()
    db.refresh(nueva_orden)
    return {
        "id": nueva_orden.id,
        "descripcion": nueva_orden.descripcion,
        "total": nueva_orden.total,
        "tipo": nueva_orden.tipo,
        "fecha": nueva_orden.fecha,
        "estado": nueva_orden.estado,
        "cliente_nombre": nueva_orden.factura_nombre,
        "cliente_rtn": nueva_orden.factura_rtn or "Consumidor Final",
        "cliente_dni": nueva_orden.factura_dni or "N/A"
    }

# Cajero: Ver Ordenes Pendientes de Cobro
@app.get("/caja/pendientes")
def listar_pendientes(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    # Unimos con la tabla de clientes para obtener nombre y RTN para la búsqueda
    query = db.query(models.OrdenTrabajo, models.Cliente).join(
        models.Cliente, models.OrdenTrabajo.cliente_id == models.Cliente.id
    ).filter(models.OrdenTrabajo.estado == "Pendiente", models.OrdenTrabajo.tipo == "Orden").all()
    
    return format_ordenes_pago(query)

@app.get("/caja/cotizaciones")
def listar_cotizaciones(db: Session = Depends(get_db), current_user: models.Usuario = Depends(get_current_user)):
    query = db.query(models.OrdenTrabajo, models.Cliente).join(
        models.Cliente, models.OrdenTrabajo.cliente_id == models.Cliente.id
    ).filter(models.OrdenTrabajo.tipo == "Cotizacion", models.OrdenTrabajo.estado == "Pendiente").all()
    
    return format_ordenes_pago(query)

@app.put("/ordenes/{orden_id}/facturacion")
def actualizar_facturacion_orden(
    orden_id: int, 
    data: FacturacionUpdate,
    db: Session = Depends(get_db), 
    current_user: models.Usuario = Depends(get_current_user)):
    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not orden: raise HTTPException(status_code=404)
    
    rtn, dni = procesar_identidad(data.identidad)

    orden.factura_nombre = data.nombre
    orden.factura_rtn = rtn
    orden.factura_dni = dni
    db.commit()
    return {"message": "Datos de facturación actualizados"}

# Cajero: Realizar Cobro
@app.post("/caja/cobrar/{orden_id}")
def cobrar_orden(
    orden_id: int,
    cobro: CobroRequest,
    db: Session = Depends(get_db), 
    current_user: models.Usuario = Depends(get_current_user)):
    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not orden: raise HTTPException(status_code=404, detail="Orden no encontrada")
    orden.estado = "Pagada"
    orden.metodo_pago = cobro.metodo_pago
    orden.referencia_pago = cobro.referencia_pago
    orden.comprobante_pago = cobro.comprobante

    # Descontar del inventario
    items_raw = orden.descripcion.split(';')
    for raw in items_raw:
        if not raw: continue
        parts = raw.split('|')
        if len(parts) == 3:
            cant = int(parts[0])
            nombre = parts[1]
            item_db = db.query(models.ItemCatalogo).filter(models.ItemCatalogo.nombre == nombre).first()
            if item_db and item_db.tipo == "Producto":
                item_db.existencia -= cant
                
    db.commit()
    return {"message": "Cobro realizado con éxito"}

# Admin: Listar Facturas Pagadas
@app.get("/caja/pagadas")
def listar_pagadas(db: Session = Depends(get_db), user: models.Usuario = Depends(check_cajero_or_admin)):
    query = db.query(models.OrdenTrabajo, models.Cliente).join(
        models.Cliente, models.OrdenTrabajo.cliente_id == models.Cliente.id
    ).filter(models.OrdenTrabajo.estado.in_(["Pagada", "Anulada"])).all()
    
    return format_ordenes_pago(query)

@app.get("/reportes/egresos", response_model=List[EgresoResponse])
def listar_egresos(db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    return db.query(models.Egreso).order_by(models.Egreso.fecha.desc()).all()

@app.get("/reportes/rendimiento")
def reporte_rendimiento(db: Session = Depends(get_db), admin: models.Usuario = Depends(check_admin)):
    # Obtener trabajos completados que tienen registro de tiempo
    trabajos = db.query(models.OrdenTrabajo, models.Usuario.username).join(
        models.Usuario, models.OrdenTrabajo.mecanico_id == models.Usuario.id
    ).filter(
        models.OrdenTrabajo.taller_completado == True,
        models.OrdenTrabajo.inicio_trabajo != None,
        models.OrdenTrabajo.fin_trabajo != None
    ).all()

    stats = {}
    for orden, name in trabajos:
        if name not in stats:
            stats[name] = {"total_trabajos": 0, "tiempo_total_segundos": 0}
        
        # Calcular duración en segundos
        duracion = (orden.fin_trabajo - orden.inicio_trabajo).total_seconds()
        stats[name]["total_trabajos"] += 1
        stats[name]["tiempo_total_segundos"] += duracion

    resultado = []
    for name, data in stats.items():
        promedio_minutos = (data["tiempo_total_segundos"] / data["total_trabajos"]) / 60
        resultado.append({
            "mecanico": name,
            "trabajos_completados": data["total_trabajos"],
            "tiempo_promedio_min": round(promedio_minutos, 2)
        })
    return resultado

def format_ordenes_pago(query):
    return [{
        "id": o.id,
        "descripcion": o.descripcion,
        "total": o.total,
        "tipo": o.tipo,
        "fecha": o.fecha,
        "estado": o.estado,
        "cliente_nombre": o.factura_nombre or c.nombre,
        "cliente_rtn": o.factura_rtn or c.rtn or "Consumidor Final",
        "cliente_dni": o.factura_dni or c.dni or "N/A",
        "metodo_pago": o.metodo_pago,
        "referencia_pago": o.referencia_pago,
        "comprobante_pago": o.comprobante_pago
    } for o, c in query]

# Admin/Cajero: Convertir Cotización a Orden (Enviar a Caja)
@app.post("/caja/convertir-cotizacion/{orden_id}")
def convertir_cotizacion(orden_id: int, db: Session = Depends(get_db), user: models.Usuario = Depends(check_cajero_or_admin)):
    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id, models.OrdenTrabajo.tipo == "Cotizacion").first()
    if not orden:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    
    orden.tipo = "Orden"
    orden.fecha = datetime.now(timezone.utc) # Actualizamos la fecha al momento de convertir
    db.commit()
    return {"message": "Cotización enviada a caja exitosamente"}

# Admin/Cajero: Anular Factura (Cancelar definitivamente)
@app.post("/caja/anular/{orden_id}")
def anular_factura(orden_id: int, db: Session = Depends(get_db), user: models.Usuario = Depends(check_cajero_or_admin)):
    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not orden: raise HTTPException(status_code=404, detail="Orden no encontrada")
    orden.estado = "Anulada"
    db.commit()
    return {"message": "Factura anulada exitosamente"}

# Pantalla Taller: Asignarse un trabajo
@app.post("/taller/asignar/{orden_id}")
def asignar_trabajo(orden_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(check_mecanico_or_admin)):
    # Verificar si el mecánico ya tiene un trabajo activo
    trabajo_activo = db.query(models.OrdenTrabajo).filter(
        models.OrdenTrabajo.mecanico_id == current_user.id,
        models.OrdenTrabajo.taller_completado == False
    ).first()
    
    if trabajo_activo:
        raise HTTPException(status_code=400, detail="Ya tienes un trabajo en progreso. Termínalo antes de tomar otro.")

    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if orden.mecanico_id:
        raise HTTPException(status_code=400, detail="Este trabajo ya fue tomado por otro mecánico")

    orden.mecanico_id = current_user.id
    orden.inicio_trabajo = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Trabajo asignado e iniciado"}

# Pantalla Taller: Marcar trabajo como completado
@app.post("/taller/completar/{orden_id}")
def completar_trabajo(orden_id: int, db: Session = Depends(get_db), current_user: models.Usuario = Depends(check_mecanico_or_admin)):
    orden = db.query(models.OrdenTrabajo).filter(models.OrdenTrabajo.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if orden.mecanico_id != current_user.id and current_user.rol != "admin":
        raise HTTPException(status_code=403, detail="No puedes completar un trabajo asignado a otro mecánico")

    orden.fin_trabajo = datetime.now(timezone.utc)
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
        "estado_pago": o.estado,
        "mecanico_id": o.mecanico_id,
        "inicio_trabajo": o.inicio_trabajo
    } for o, c, v in query]
