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