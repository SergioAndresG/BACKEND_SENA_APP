from pydantic import BaseModel
from enum import Enum

class Rol(str, Enum):
    INSTRUCTOR = "INSTRUCTOR"
    ADMINISTRADOR = "ADMINISTRADOR"
