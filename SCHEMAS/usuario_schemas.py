from pydantic import BaseModel
from enum import Enum
from typing import Optional

class Rol(str, Enum):
    INSTRUCTOR = "INSTRUCTOR"
    ADMINISTRADOR = "ADMINISTRADOR"

class UsuarioGenerador(BaseModel):
    id: Optional[int] = None
    nombre: str
    apellidos: str
    correo: str
    rol: Rol

    class Config:
        orm_mode = True

class UsuarioCreate(BaseModel):
    nombre: str
    apellidos: str
    correo: str
    rol: str

class UsuarioResponse(BaseModel):
    id: int
    nombre: str
    apellidos: str
    correo: str
    rol: Rol
    contraseña: str

    class Config:
        orm_mode = True

class UsuarioDelete(BaseModel):
    contraseña_admin: str

    class Config:
        orm_mode = True