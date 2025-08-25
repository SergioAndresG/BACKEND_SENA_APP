from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from connection import base

from datetime import datetime

class ArchivoExcel(base):
    __tablename__ = "archivos_excel"
    
    id = Column(Integer, primary_key=True, autoincrement=True)

    #Información del archivo
    nombre_original = Column(String(255), nullable=False)
    nombre_interno = Column(String(500), nullable=False)  # Nombre del archivo en el servidor
    ruta_archivo = Column(String(500), nullable=False)  # Ruta donde se guarda el archivo

    #Informacion de contenido
    ficha = Column(String(20), nullable=False)  # Número de ficha asociado
    modalidad = Column(String(50), nullable=False)  # Modalidad del archivo (grupal, individual, etc.)
    cantidad_aprendices = Column(BigInteger, nullable=False)  # Cantidad de aprendices en el archivo
    
    # Relación individual con aprendiz vía documento
    aprendiz_documento = Column(String(20), ForeignKey("Aprendices.documento"), nullable=True)
    aprendiz = relationship("Aprendiz", back_populates="archivos_excel")

    #Seguridad y validación
    hash_archivo = Column(String(64), nullable=False)  # Hash del archivo para verificar integridad
    tamaño_bytes = Column(BigInteger, nullable=False)  # Tamaño del archivo en bytes

    #Control de esatdo
    activo = Column(Boolean, default=True)  # Para soft delete
    fecha_creacion = Column(DateTime, default=datetime.now)
    fecha_modificacion = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Usuario que subió el archivo
    usuario_id = Column(Integer, ForeignKey('Usuarios.id'))  # ID del usuario que subió el archivo
    usuario = relationship("Usuarios", back_populates="archivos_generados")



