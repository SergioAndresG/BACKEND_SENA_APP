from fastapi import APIRouter, HTTPException, Depends, status, Response, Request
from sqlalchemy.orm import Session
from connection import get_db
from MODELS import Usuarios
from MODELS.token_blacklist import TokenBlacklist
from SCHEMAS.login_schemas import LoginSchema, UserResponse
from datetime import datetime, timedelta, timezone
import logging
from FUNCIONES.FUNCIONES_TOKENS.tokens_service import (
    create_access_token, 
    create_refresh_token, 
    verify_token, 
    get_current_user,
    pwd_context,
    oauth2_scheme,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)

#-> Definimos el enrutador a usar en el main
router_login = APIRouter()


# utilizamos los loggers para mostrar informacion
logging.basicConfig(level=logging.INFO) #-> mostrara información a nivel de INFO o superior
logger = logging.getLogger(__name__) #-> usando como nombre el modulo actual


# Definimos el endpoint para inicio de sesión
@router_login.post("/login")
# -> Función asincrónica que recibe:
#    "response" para poder setear cookies,
#    "login_data" con las credenciales del usuario,
#    y una sesión activa a la base de datos.
async def login(response: Response, login_data: LoginSchema, db: Session = Depends(get_db)):
    # Log: mostramos quién intenta iniciar sesión
    logger.info(f"Intento de inicio de sesión para: {login_data.correo}")
    
    # Verificar si el usuario existe en la base de datos
    user = db.query(Usuarios).filter(Usuarios.correo == login_data.correo).first()
    
    # Si el usuario no existe o la contraseña no coincide, devolvemos error
    if not user or not pwd_context.verify(login_data.contraseña, user.contraseña):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

    # ==================== CREACIÓN DE TOKENS ====================
    token_data = {
        "sub": user.correo,  # sujeto del token (correo del usuario)
        "user_id": user.id,  # identificador único en la BD
        "rol": user.rol      # rol del usuario (permisos)
    }
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # duración del access token
    access_token = create_access_token(data=token_data, expires_delta=access_token_expires)  # token de acceso
    refresh_token = create_refresh_token(data=token_data)  # token de refresco
    
    # ==================== COOKIE DEL REFRESH TOKEN ====================
    response.set_cookie(
        key="refresh_token",   # nombre de la cookie
        value=refresh_token,   # contenido: el refresh token firmado
        httponly=True,         # inaccesible desde JavaScript (protección XSS)
        samesite="lax",        # evita envío en cross-site requests (protección CSRF)
        secure=False,          # False en desarrollo, True en producción con HTTPS
        max_age=60 * 60 * 24 * REFRESH_TOKEN_EXPIRE_DAYS,  # tiempo de vida de la cookie
        path="/",              # disponible en todo el backend
        # domain=None,         # dominio explícito (configurar en producción si se usa frontend aparte)
    )
    
    # Loggers de depuración (quitar en producción)
    logger.info(f"✅ Login exitoso para: {user.correo}")
    logger.info(f"🍪 Cookie refresh_token configurada: {refresh_token[:20]}...")
    
    # ==================== RESPUESTA ====================
    user_response = UserResponse(
        id=user.id, nombre=user.nombre, apellidos=user.apellidos, correo=user.correo, rol=user.rol
    )
    
    # Retornamos el access_token (para autenticación inmediata)
    # y dejamos el refresh_token en cookie (para renovaciones futuras)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response
    }


# Endpoint para cierre de sesión: invalida el access token y elimina la cookie refresh_token.
@router_login.post("/logout")
# -> Función asincrónica que recibe:
# -> "response": para dar respuesta al frontend
# -> "db": sesion en la base de datos
# -> "token": token que espera recibir para invalidar
async def logout(response: Response, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # si el token existe hacemos la siguiente operación
    if token:
        try:
            # verificamos el pauload del token, que sea tipo "access"
            payload = verify_token(token, db, expected_type="access")
            # obtenemos el jti "identificador unico"
            jti = payload.get("jti")
            # obtenemos la expiracion
            exp = payload.get("exp")
            # si ambos existen realizamos la siguiente operación
            if jti and exp:
                # primero convertimos a datetime, formato legible para python
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) #-> UTC, estandar de JWT
                db.add(TokenBlacklist(jti=jti, expires_at=expires_at)) # -> despúes agregamos ese access token a el blacklist
                db.commit() #-> actualizamos la base de datos
        except HTTPException:
            # Ignorar si el token ya es inválido, el objetivo es desloguear
            pass
    # Eliminar la cookie de refresh token
    response.delete_cookie("refresh_token")

    # Nota: no retorna datos, solo elimina la cookie y asegura que el access token no sea reutilizable.




# Definimos endpoint para redrescar el access_token usando el refresh_token
@router_login.post("/refresh")
# -> Función asincrónica que recibe:
# -> "request": la peticion del frontend
# -> "response": para dar respuesta al frontned
# -> "db": sesión en la base de datos
async def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        # === DEBUG DE COOKIES Y HEADERS ===
        # Revisamos cookies y origen de la petición para depurar (en este momento solo desarrollo)
        logger.info("=== DEBUG REFRESH ===")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Cookies recibidas: {request.cookies}")
        logger.info(f"Origin: {request.headers.get('origin', 'NO_ORIGIN')}")
        logger.info(f"Referer: {request.headers.get('referer', 'NO_REFERER')}")
        
        # === VERIFICACIÓN DEL REFRESH TOKEN ===
        # guardamos en una variable el cuerpo de la cookie
        refresh_token = request.cookies.get("refresh_token")
        # si no llega nada retornamos un errir mostramos lo que esta disponible, y devolvemos un error 401
        if not refresh_token:
            logger.warning("❌ No se encontró cookie refresh_token")
            logger.info(f"Cookies disponibles: {list(request.cookies.keys())}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found in cookies"
            )
        
        # al encontrar mostramos la cookie obtenida
        logger.info(f"✅ Refresh token encontrado: {refresh_token[:20]}...")
        
        # Verificar el refresh token (que cumpla con lo que la función solicita)
        payload = verify_token(refresh_token, db, expected_type="refresh")
        

        # === INVALIDACION DE TOKENS ===
        old_jti = payload.get("jti") #-> guardamos en una variable, el identificador unico "viejo"
        old_exp = payload.get("exp") #-> guardamos en una variable, la expiracion del token
        if old_jti and old_exp: # -> si ambas existen realizamos la siguiente operacion
            try:
                # guardamos en datatime legible para python
                expires_at = datetime.fromtimestamp(old_exp, tz=timezone.utc) # -> aseguramos que se interprete en UTC, el estandat de los JWT
                db.add(TokenBlacklist(jti=old_jti, expires_at=expires_at)) # -> agregamos a la balck list en la base de datos
                db.commit() # -> actualizamos
                logger.info(f"Token antiguo añadido a blacklist: {old_jti}") # -> mostramos que se agrego correctamente
            except Exception as e:
                logger.error(f"Error añadiendo token a blacklist: {str(e)}") # -> si algo falla lanzamos la excepcion

        # Verificar usuario, del token
        user_email = payload.get("sub")
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
            
        # Hacemos una consulata  al base de datos para verificar el usuario
        user = db.query(Usuarios).filter(Usuarios.correo == user_email).first()
        if not user:
            logger.warning(f"Usuario no encontrado: {user_email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="User not found"
            )

        # Crear nuevos tokens
        token_data = {"sub": user.correo, "user_id": user.id, "rol": user.rol}
        new_access_token = create_access_token(
            data=token_data, 
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        # creamos un refresh token con la informacion del token
        new_refresh_token = create_refresh_token(data=token_data)

        # Establecer nueva cookie
        response.set_cookie(
            key="refresh_token", #-> nombre de la cookie
            value=new_refresh_token, # -> contenido: el token refresh creado
            httponly=True, # -> inaccesible desde JavaScript (proytección XSS)
            samesite="lax", # -> evita envío en cross-site requests (proytección CSRF)
            secure=False, # -> False en desarrollo, True en producción con HTTPS
            max_age=60 * 60 * 24 * REFRESH_TOKEN_EXPIRE_DAYS, # -> la duraccion del refresh token
            path="/"# -> disponible en todo el backend
        )
        
        # Loggers de depuración (quitar en producción)
        logger.info(f"✅ Refresh exitoso para: {user.correo}")
        logger.info(f"🍪 Nueva cookie refresh_token configurada: {new_refresh_token[:20]}...")
        
        # Retornamos el nuevo access_token al frontend en el cuerpo de la respuesta.
        # El refresh_token NO se retorna en el body, solo en la cookie para mayor seguridad.
        return {
            "access_token": new_access_token, 
            "token_type": "bearer"
        }
        
    # Si la operación falla retornamos una Excepción 
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado en refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )

@router_login.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Usuarios = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Se requiere autenticación")
    return current_user
