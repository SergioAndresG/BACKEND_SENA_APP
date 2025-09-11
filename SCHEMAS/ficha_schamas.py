from pydantic import BaseModel


class informacionAdicional(BaseModel):
  nivel_formacion: str
  modalidad_formacion: str
  trimestre: str
  fecha_inicio_etapa_productiva: str
  jornada: str