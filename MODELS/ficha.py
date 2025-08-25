from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from connection import base

class Ficha(base):
    __tablename__ = "Fichas"
    numero_ficha = Column(String(10), primary_key=True)
    programa = Column(String(200), nullable=True)
    estado = Column(String(100), nullable=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    fecha_reporte = Column(Date, nullable=True)
    fecha_inicio_prod = Column(Date, nullable=True)
    trimeste = Column(String(50), nullable=True)
    jornada = Column(String(50), nullable=True)
    modalidad = Column(String(50), nullable=True)

    aprendices = relationship("Aprendiz", back_populates="ficha")