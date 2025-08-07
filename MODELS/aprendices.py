from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from connection import base

class Aprendiz(base):
    __tablename__ = "Aprendices"
    id_aprendiz = Column(Integer, primary_key=True, autoincrement=True)
    documento = Column(String(20), nullable=False)  
    nombre = Column(String(100), nullable=False)    
    apellido = Column(String(100), nullable=False)  
    correo = Column(String(100), nullable=False)    
    celular = Column(String(20), nullable=False)
    direccion = Column(String(200), nullable=True)
    tipo_documento = Column(String(10), nullable=True)  
    estado = Column(String(50), nullable=True)

    # Clave foránea para ficha
    ficha_numero = Column(String(20), ForeignKey("Fichas.numero_ficha"))

    # Relación con ficha
    ficha = relationship("Ficha", back_populates="aprendices")