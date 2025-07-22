from pydantic import BaseModel
from typing import List
from typing import Optional

class AprendizParaExportar(BaseModel):
    tipo_documento: str
    documento: str
    nombre: str
    apellidos: str
    direccion: str
    correo: str
    celular: str
    discapacidad: str
    tipo_discapacidad: str
    firma: str

class ExportarF165Request(BaseModel):
    modalidad: str
    aprendices: List[AprendizParaExportar]

    
