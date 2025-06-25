from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from connection import base

class Ficha(base):
    __tablename__ = "Fichas"
    numero_ficha = Column(String(10), primary_key=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    aprendices = relationship("Aprendices", back_populates="ficha")