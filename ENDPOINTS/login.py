from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from connection import get_db
from MODELS import Usuarios
from SCHEMAS.login_schemas import Token, LoginSchema, UserResponse
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import re
import logging

SECRET_KEY = "12345678910"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router_login = APIRouter()

def verify_password(plain_password, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_pass: str = payload.get("sub")
        if user_pass is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(Usuarios).filter(Usuarios.contraseña == user_pass).first()
    if user is None:
        raise credentials_exception
    return user

def sanitize_input(input_str: str) -> str:
    # Elimina caracteres potencialmente peligrosos
    if not input_str:
        return ""
    
    # Remover caracteres peligrosos
    dangerous_patterns = [
        r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)",
        r"[<>\"'%;()&+]",
        r"--",
        r"/\*",
        r"\*/"
    ]

    sanitized = input_str.strip()
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, "", sanitized)

    return sanitized

#este endpoint es para hashear las contraseñas (ya que se inserto los usuarios desde la base de datos)
@router_login.post("/hasheo-password")
async def hash(db: Session=Depends(get_db)):
    usuario = db.query(Usuarios).all()
    for user in usuario:
        if not pwd_context.identify(user.contraseña): #si no hay hash de la contraseña
            user.contraseña = pwd_context.hash(user.contraseña)
    db.commit()
    return {"menssage": "Contraseñas hasheadas correctamente"}


@router_login.post("/login/", response_model=Token)
async def login(login_data: LoginSchema, db: Session = Depends(get_db)):
    """
    Endpoint para iniciar sesión de usuario.

    Args:
        usuario (Usuarios): Objeto con las credenciales del usuario.
        db (Session): Sesión de base de datos.

    Returns:
        Mensaje de éxito o error.
    """
    try:
        correo = sanitize_input(login_data.correo)

        logger.info(f"Intento de inicio de sesión para el Correo: {correo}")
        user = db.query(Usuarios).filter(Usuarios.correo == correo).first()

        # Verificar si el usuario existe y la contraseña es correcta
        if not user or not verify_password(login_data.contraseña, user.contraseña):
            # Log de intento fallido
            logger.warning(f"Intento de login fallido para el contraseña: {correo}")
            
            # Respuesta genérica para no dar pistas sobre qué falló
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )
        
        # Crear token de acceso
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.correo, "user_id": user.id, "rol": user.rol},
            expires_delta=access_token_expires
        )

                # Log de login exitoso
        logger.info(f"Login exitoso para usuario: {user.correo}")
        
        # Crear respuesta del usuario (sin contraseña)
        user_response = UserResponse(
            id=user.id,
            nombre=user.nombre,
            apellidos=user.apellidos,
            correo=user.correo,
            rol=user.rol
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router_login.get("/protected/")
async def protected_route(current_user: Usuarios = Depends(get_current_user)):
    """
    Ruta protegida de ejemplo
    """
    return {"message": f"Hola {current_user.nombre}, esta es una ruta protegida"}


@router_login.get("/me/", response_model=UserResponse)
async def get_current_user_info(current_user: Usuarios = Depends(get_current_user)):
    """
    Obtiene la información del usuario actualmente logueado
    """
    try:
        logger.info(f"Solicitando información del usuario: {current_user.correo}")
        
        return UserResponse(
            id=current_user.id,
            nombre=current_user.nombre,
            apellidos=current_user.apellidos,
            correo=current_user.correo,
            rol=current_user.rol
        )
    except Exception as e:
        logger.error(f"Error al obtener información del usuario: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener información del usuario"
        )