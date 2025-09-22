from MODELS.a_usuarios import Usuarios
from fastapi import APIRouter, HTTPException, Depends
from SCHEMAS.usuario_schemas import UsuarioResponse, Rol, UsuarioCreate, UsuarioDelete
from sqlalchemy.orm import Session
from FUNCIONES.FUNCIONES_USUARIOS.generador_contraseñas import generar_contraseña
from typing import List
from connection import get_db
import bcrypt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router_usuarios = APIRouter()

# Obtener todos los usuarios
@router_usuarios.get("/usuarios/", response_model=List[UsuarioResponse])
async def obtener_usuarios(db: Session = Depends(get_db)):
    try:
        usuarios = db.query(Usuarios).all()
        return usuarios
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Eliminar un usuario por su ID
@router_usuarios.post("/usuarios/{usuario_id}", status_code=204)
async def eliminar_usuario(usuario_id: int, eliminar_request: UsuarioDelete, db: Session = Depends(get_db)):
    """
    Elimina un usuario de la base de datos por su ID.

    Args:
        usuario_id (int): ID del usuario a eliminar.
        db (Session): Sesión de base de datos.

    Raises:
        HTTPException: Si el usuario no existe.
    """
    admin = db.query(Usuarios).filter(Usuarios.rol == Rol.ADMINISTRADOR).first()
    if not admin:
        raise HTTPException(status_code=400, detail="La contraseña del administrador es requerida")

    # si la contraseña es distinta a la proporcionada, lanzar error
    if not bcrypt.checkpw(eliminar_request.contraseña_admin.encode('utf-8'), admin.contraseña.encode('utf-8')):
        raise HTTPException(status_code=403, detail="Contraseña de administrador incorrecta")

    usuario = db.query(Usuarios).filter(Usuarios.id == usuario_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    try:
        db.delete(usuario)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
# Crear un nuevo usuario
@router_usuarios.post("/usuarios/", response_model=UsuarioResponse)
async def crear_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):

    """
    Crea un nuevo usuario en la base de datos.

    Args:
        usuario (UsuarioGenerador): Datos del usuario a crear.
        db (Session): Sesión de base de datos.

    Returns:
        UsuarioGenerador: Datos del usuario creado.
    """

    contraseña = generar_contraseña()
    
    try:
        nuevo_usuario = Usuarios(
            nombre=usuario.nombre,
            apellidos=usuario.apellidos,
            correo=usuario.correo,
            rol=Rol(usuario.rol),
            contraseña=contraseña
        )
        if nuevo_usuario:
            if not pwd_context.identify(nuevo_usuario.contraseña):
                nuevo_usuario.contraseña = pwd_context.hash(nuevo_usuario.contraseña)

        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)

        return UsuarioResponse(
            id=nuevo_usuario.id,
            nombre=nuevo_usuario.nombre,
            apellidos=nuevo_usuario.apellidos,
            correo=nuevo_usuario.correo,
            rol=nuevo_usuario.rol,
            contraseña=contraseña
        )
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router_usuarios.put("/usuarios/{usuario_id}", response_model=UsuarioResponse)
async def actualizar_usuario(usuario_id: int, usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """
    Actualiza los datos de un usuario existente en la base de datos.

    Args:
        usuario_id (int): ID del usuario a actualizar.
        usuario (UsuarioGenerador): Datos del usuario a actualizar.
        db (Session): Sesión de base de datos.

    Returns:
        UsuarioGenerador: Datos del usuario actualizado.
    """
    usuario_db = db.query(Usuarios).filter(Usuarios.id == usuario_id).first()

    if not usuario_db:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    try:
        usuario_db.nombre = usuario.nombre
        usuario_db.apellidos = usuario.apellidos
        usuario_db.correo = usuario.correo
        usuario_db.rol = Rol(usuario.rol)
        
        db.commit()
        db.refresh(usuario_db)
        
        return UsuarioResponse(
            id=usuario_db.id,
            nombre=usuario_db.nombre,
            apellidos=usuario_db.apellidos,
            correo=usuario_db.correo,
            rol=usuario_db.rol,
            contraseña=usuario_db.contraseña
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router_usuarios.patch("/usuarios/{usuario_id}", response_model=UsuarioResponse)
async def cambiar_contraseña(usuario_id: int, db: Session = Depends(get_db)):
    """
    Obtiene los datos de un usuario por su ID.

    Args:
        usuario_id (int): ID del usuario a obtener.
        db (Session): Sesión de base de datos.

    Returns:
        UsuarioGenerador: Datos del usuario.
    """
    try:
        usuario = db.query(Usuarios).filter(Usuarios.id == usuario_id).first()
        
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        contraseña = generar_contraseña()


        try:
            usuario.contraseña = contraseña
            print(contraseña)
            if not pwd_context.identify(usuario.contraseña):
                usuario.contraseña = pwd_context.hash(usuario.contraseña)
            

            db.commit()
            db.refresh(usuario)
        except Exception as e:
            db.rollback()

        return UsuarioResponse(
            id=usuario.id,
            nombre=usuario.nombre,
            apellidos=usuario.apellidos,
            correo=usuario.correo,
            rol=usuario.rol,
            contraseña=contraseña
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
