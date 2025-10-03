from fastapi import HTTPException, APIRouter, Depends
from SCHEMAS.aprendiz_schemas import ExportarF165Request
from fastapi.responses import FileResponse
from connection import get_db
from sqlalchemy.orm import Session
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
import base64
import os
from datetime import datetime
from io import BytesIO
from fastapi.responses import StreamingResponse
from FUNCIONES.FUNCIONES_FORMATOS.formato_service import FormatoService
from MODELS import ArchivoExcel, Usuarios, Ficha
from pathlib import Path
import hashlib
import tempfile
import asyncio
from concurrent.futures import ThreadPoolExecutor
from openpyxl.styles import Font 
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage

router_format = APIRouter()

format_service = FormatoService()

UPLOAD_DIR = "archivos_exportados"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@router_format.post("/exportar-f165")
async def exportar_f165(request: ExportarF165Request, db: Session = Depends(get_db)):

    if not request.aprendices:
        raise HTTPException(status_code=400, detail="Lista de aprendices vacía")

    modalidad = request.modalidad # 'grupal' o 'individual'
    aprendices = request.aprendices # Lista de aprendices a exportar
    usuario_gene = request.usuario_generator # Usuario que genera el archivo
    informacion_adicional = request.informacion_adicional # Información adicional

    imagenes_procesadas = await format_service.procesar_firmas_en_paralelo(aprendices)

    try:
        archivo_db, ruta_completa = format_service.crear_y_guardar_formato_f165(
            db=db,
            request=request,
            modalidad=modalidad,
            aprendices=aprendices,
            usuario_gene=usuario_gene,
            informacion_adicional=informacion_adicional,
            imagenes_procesadas=imagenes_procesadas
        )

        for imagen_path in imagenes_procesadas:
            if imagen_path and os.path.exists(imagen_path):
                os.unlink(imagen_path)

        return FileResponse(
            path=ruta_completa,
            filename=archivo_db.nombre_original,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router_format.get("/archivos/usuario/{usuario_id}")
def obtener_archivos_por_usuario(usuario_id: int, db: Session = Depends(get_db)):
    archivos = db.query(ArchivoExcel).filter(ArchivoExcel.usuario_id == usuario_id, ArchivoExcel.activo == True).all()
    return archivos


@router_format.get("/archivo/ficha/{ficha}")
def obtener_archivo_por_ficha(ficha: str, db: Session = Depends(get_db)):
    archivos = db.query(ArchivoExcel).filter(ArchivoExcel.ficha == ficha, ArchivoExcel.activo == True).all()

    if not archivos:
        raise HTTPException(status_code=404, detail="No se encontraron archivos para esta ficha")

    return [ 
        {
            "id": archivo.id,
            "nombre_original": archivo.nombre_original,
            "modalidad": archivo.modalidad,
            "cantidad_aprendices": archivo.cantidad_aprendices,
            "fecha_creacion": archivo.fecha_creacion.isoformat(),
            "usuario": {
                "nombre": archivo.usuario.nombre,
                "apellidos": archivo.usuario.apellidos,
                "rol": archivo.usuario.rol
            }
        }
        for archivo in archivos
    ]

@router_format.get("/archivo/historial")
def obtener_historila_completo(db: Session = Depends(get_db)):
    archivos = db.query(ArchivoExcel).join(Usuarios).filter(ArchivoExcel.activo == True).order_by(ArchivoExcel.fecha_creacion.desc()).all()

    return [
        {       
            "id": archivo.id,
            "nombre_original": archivo.nombre_original,
            "ficha": archivo.ficha,
            "modalidad": archivo.modalidad,
            "cantidad_aprendices": archivo.cantidad_aprendices,
            "fecha_creacion": archivo.fecha_creacion.isoformat(),
            "tamaño_mb": round(archivo.tamaño_bytes / 1024 / 1024, 2),  # Convertir a MB
            "generado_por":  f"{archivo.usuario.nombre} {archivo.usuario.apellidos}",
            "rol_usuario": archivo.usuario.rol
        }
        for archivo in archivos
    ]

@router_format.get("/historial-exportaciones")
def obtener_historial(db: Session = Depends(get_db)):
    """
    Obtiene el historial de exportaciones de formatos F165.
    """
    archivos = db.query(ArchivoExcel)\
    .filter(ArchivoExcel.activo == True)\
    .order_by(ArchivoExcel.fecha_creacion.desc())\
    .limit(100)\
    .all()

    return [
        {
            "id": archivo.id,
            "nombre_": archivo.nombre_original,
            "ruta_archivo": archivo.ruta_archivo,
            "ficha": archivo.ficha,
            "modalidad": archivo.modalidad,
            "cantidad_aprendices": archivo.cantidad_aprendices,
            "fecha_creacion": archivo.fecha_creacion.isoformat(),
            "usuario_id": archivo.usuario_id,
            "usuario_nombre": archivo.usuario.nombre,
            "usuario_apellidos": archivo.usuario.apellidos,
            "tamaño_mb": round(archivo.tamaño_bytes / 1024 / 1024, 2)  # Convertir a MB
        }
        for archivo in archivos
    ]

@router_format.get("/descargar-archivo/{id_archivo}")
def descargar_archivo(id_archivo: int, db: Session = Depends(get_db)):
    archivo_descargar = db.query(ArchivoExcel).filter(ArchivoExcel.id == id_archivo).first()

    ruta_completa = os.path.join(UPLOAD_DIR, archivo_descargar.ruta_archivo)
    
    return FileResponse(
        path=ruta_completa,
        filename=archivo_descargar.nombre_original,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
