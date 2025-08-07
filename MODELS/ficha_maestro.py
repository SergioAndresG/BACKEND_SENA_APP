from sqlalchemy import Column, Integer, String, Date


from connection import base


class FichaMaestro(base):
    __tablename__ = "FichasMaestro"
    numero_ficha = Column(String(10), primary_key=True)
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    fecha_actualizacion = Column(Date, nullable=True)  # Para saber cuándo se actualizó
    
    def __repr__(self):
        return f"<FichaMaestro(numero_ficha={self.numero_ficha})>"