from SCHEMAS.usuario_schemas import Rol
from sqlalchemy import Column, Integer, String, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from connection import base


class Usuarios(base): 
    __tablename__ = "Usuarios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    rol = Column(Enum(Rol), nullable=False)
    contraseña = Column(String(255), nullable=False)

