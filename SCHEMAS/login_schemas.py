from pydantic import BaseModel, validator
import re

class LoginSchema(BaseModel):
    correo: str
    contraseña: str

    @validator('correo')
    def validate_email(cls, v):
        dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/', 'DROP', 'SELECT', 'INSERT', 'UPDATE', 'DELETE']
        email_upper = v.upper()
        for char in dangerous_chars:
            if char in email_upper:
                raise ValueError('Email contiene caracteres no válidos')
        return v.lower().strip()
    
    @validator('contraseña')
    def validate_contraseña(cls, v):
        if len(v) < 8:
            raise ValueError('La contraseña debe tener al menos 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('La contraseña debe contener al menos una letra mayúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('La contraseña debe contener al menos una letra minúscula')
        if not re.search(r'[0-9]', v):
            raise ValueError('La contraseña debe contener al menos un número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_-]', v):
            raise ValueError('La contraseña debe contener al menos un carácter especial')
        return v
    

class UserResponse(BaseModel):
    id: int
    rol: str
    nombre: str
    apellidos: str
    correo: str

# El refresh_token ya no se envía en el cuerpo, se enviará en una cookie HttpOnly
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
