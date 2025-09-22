from pydantic import BaseModel
from typing import Optional
import enum

class NivelFormacionEnum(str, enum.Enum):
    AUXILIAR = "AUXILIAR"
    OPERARIO = "OPERARIO"
    TECNICO = "TECNICO"
    TECNOLOGO = "TECNOLOGO"

class ModalidadEnum(str, enum.Enum):
    PRESENCIAL = "PRESENCIAL"
    VIRTUAL = "VIRTUAL"

class JornadaEnum(str, enum.Enum):
    DIURNA = "DIURNA"
    NOCTURNA = "NOCTURNA"
    MIXTA = "MIXTA"

class InformacionAdicional(BaseModel):
    nivel_formacion: NivelFormacionEnum
    modalidad_formacion: ModalidadEnum
    trimestre: Optional[str] = None
    fecha_inicio_etapa_productiva: Optional[str] = None
    jornada: JornadaEnum

    class Config:
        use_enum_values = True
