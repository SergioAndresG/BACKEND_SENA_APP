from pydantic import BaseModel
from typing import List
from typing import Optional
from .usuario_schemas import UsuarioGenerador
from .ficha_schamas import informacionAdicional
from datetime import datetime

class AprendizParaExportar(BaseModel):
    tipo_documento: str
    documento: str
    nombre: str
    apellido: str
    direccion: str
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    correo: str
    celular: str
    discapacidad: str
    tipo_discapacidad: str
    firma: str

class AprendizActualizarRequest(BaseModel):
    """Modelo para actualizar los datos de un aprendiz"""
    tipo_documento: Optional[str] = None
    documento: Optional[str] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    direccion: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    correo: Optional[str] = None
    celular: Optional[str] = None
    discapacidad: Optional[str] = None
    tipo_discapacidad: Optional[str] = None
    firma: Optional[str] = None
    editado: Optional[bool] = None

class AprendixActualizarResponse(BaseModel):
    """Modelo de respuesta para la actualización de un aprendiz"""
    success: bool
    message: str
    aprendiz_actualizado: dict

class ExportarF165Request(BaseModel):
    modalidad: str
    ficha: str
    aprendices: List[AprendizParaExportar]
    usuario_generator: UsuarioGenerador
    informacion_adicional: informacionAdicional

    
