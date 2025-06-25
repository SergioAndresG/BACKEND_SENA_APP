from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from connection import base

class Aprendiz(base):
    __tablename__ = "Aprendices"
    id_aprendiz = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False)
    apellido = Column(String(50), nullable=False)
    correo = Column(String(50), nullable=False)
    celular = Column(String(20), nullable=False)

    #Clave foranea para ficha
    ficha_numero = Column(String(10), ForeignKey("Fichas.numero_ficha"))

    #Relacion inversa con ficha
    ficha = relationship("Ficha", back_populates="aprendices")