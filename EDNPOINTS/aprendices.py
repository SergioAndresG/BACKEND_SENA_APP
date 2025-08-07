from fastapi import HTTPException, APIRouter, Depends
from SCHEMAS.aprendiz_schemas import AprendizActualizarRequest, AprendixActualizarResponse
from connection import get_db
from MODELS.aprendices import Aprendiz
from sqlalchemy.orm import Session

router_aprendices = APIRouter()


@router_aprendices.patch("/aprendices/{documento}")
async def actualizar_aprendiz(
    documento: str,
    datos_actualizacion: AprendizActualizarRequest,
    db: Session = Depends(get_db)
):
    """
    Actualiza los datos de un aprendiz dado su documento.

    Args:
        documento (str): Documento del aprendiz a actualizar.
        aprendiz_actualizacion (AprendizActualizarRequest): Datos actualizados del aprendiz.
        db: Session: Sesión de base de datos.
    
    Returns:
        Respuesta con el aprendiz actualizado.
    """
    try:
        aprendiz = db.query(Aprendiz).filter(Aprendiz.documento == documento).first()
        
        if not aprendiz:
            raise HTTPException(status_code=404, detail=f"Aprendiz con {documento} no encontrado")
        
        datos_dict = datos_actualizacion.dict(exclude_unset=True)
        for campo, valor in datos_dict.items():
            if hasattr(aprendiz, campo):
                setattr(aprendiz, campo, valor)
        
        db.commit()
        db.refresh(aprendiz)

        aprendiz_data = {
            "tipo_documento": aprendiz.tipo_documento,
            "documento": aprendiz.documento,
            "nombre": aprendiz.nombre,
            "apellido": aprendiz.apellido,
            "direccion": aprendiz.direccion,
            "correo": aprendiz.correo,
            "celular": aprendiz.celular,
            "estado": aprendiz.estado
        }

        return AprendixActualizarResponse(
            success=True,
            message="Aprendiz actualizado correctamente",
            aprendiz_actualizado=aprendiz_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






