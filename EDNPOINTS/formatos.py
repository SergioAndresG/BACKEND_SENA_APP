from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, APIRouter, Depends
from MODELS import Aprendiz, Ficha
from SCHEMAS.aprendiz_schemas import ExportarF165Request
from FUNCIONES import procesar_archivos_background
from connection import get_db, SessionLocal
from typing import List
import uuid
from fastapi.responses import FileResponse
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
import base64
from PIL import Image
import io
from datetime import datetime
from io import BytesIO
from fastapi.responses import StreamingResponse
from tempfile import NamedTemporaryFile
from FUNCIONES.FUNCIONES_FORMATOS.formato_service import FormatoService
from MODELS import ArchivoExcel


router_format = APIRouter()

format_service = FormatoService()

@router_format.post("/exportar-f165")
def exportar_f165(request: ExportarF165Request, db: SessionLocal = Depends(get_db)):
    modalidad = request.modalidad # 'grupal' o 'individual'
    aprendices = request.aprendices # Lista de aprendices a exportar

    print("Recibido:", aprendices)
    if not aprendices:
        raise HTTPException(status_code=400, detail="Lista de aprendices vacía")

    # Cargar el archivo base
    ruta_archivo = "GFPI-F-165V3FormatoSeleccionModificacionAlternativaparadesarrollarlaEtapaProductiva.xlsx"
    wb = load_workbook(ruta_archivo) # Cargar el archivo de Excel .xlsx

    # Selección de hoja según modalidad
    if modalidad == "grupal":
        hoja = wb["Selección formato 1 - Grupal"]
    elif modalidad == "individual":
        hoja = wb["Selección Modificación F2 Indiv"]
    else:
        raise HTTPException(status_code=400, detail="Modalidad no válida")

    
    fila_inicial = 18 # Los datos empiezan en la fila 18
    espacios_disponibles = 20 # La plantilla tiene 20 espacios
    aprendices_extra = len(aprendices) - espacios_disponibles

    # Inserta filas si hay más aprendices que espacios
    if aprendices_extra > 0:
        hoja.insert_rows(idx=fila_inicial + espacios_disponibles, amount=aprendices_extra)

    # Llenar los datos en las celdas
    for i, ap in enumerate(aprendices):
        fila = fila_inicial + i
        hoja[f"C{fila}"] = ap.tipo_documento
        hoja[f"D{fila}"] = ap.documento
        hoja[f"E{fila}"] = ap.nombre
        hoja[f"F{fila}"] = ap.apellidos
        hoja[f"G{fila}"] = ap.direccion
        hoja[f"H{fila}"] = ap.correo
        hoja[f"I{fila}"] = ap.celular
        if ap.discapacidad == 'No':
            hoja[f"K{fila}"] = "x"
        else:
            hoja[f"J{fila}"] = "x"
        hoja[f"L{fila}"] = ap.tipo_discapacidad
        hoja[f"M{fila}"] = "x"
        
        firma_data = ap.firma
        
        # Eliminar encabezado si existe
        if "," in firma_data:
            firma_data = firma_data.split(",")[1]

        # Convierte la firma de base64 a imagen
        firma_bytes = base64.b64decode(firma_data)
        with NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file.write(firma_bytes)
            tmp_file_path = tmp_file.name
            
        # Insertar imagen en la celda correspondiente
        img = OpenpyxlImage(tmp_file_path)
        img.width = 80  # ajusta según tu formato
        img.height = 30

        # Supongamos que quieres insertar en la columna AG de la fila i
        celda_firma = f"AG{fila}"
        img.anchor = celda_firma

        hoja.add_image(img)

    # Guardar en memoria y retornar
    output = BytesIO() # Crea un buffer en memoria
    wb.save(output) # Guarda el archivo en el memmoria
    output.seek(0) # Vuelve al inicio del buffer
    contenido_bytes = output.getvalue() # Obtiene los bytes del archivo

    nombre_original = f"formato_F165_{modalidad}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    
    archivo_db = format_service.guardar_archivo_seguro(
        contenido_bytes=contenido_bytes,
        nombre_archivo=nombre_original,
        ficha=request.ficha,
        modalidad=modalidad,
        cantidad_aprendices=len(aprendices),
        usuario_id= request.usuario_id if request.usuario_id else None
    )

    db.add(archivo_db)
    db.commit()
    db.refresh(archivo_db)

    #retornar para desacarga
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=formato_F165.xlsx"
        }
    )

@router_format.get("/historial-exportaciones")
def obtener_historial(db: SessionLocal = Depends(get_db)):
    """
    Obtiene el historial de exportaciones de formatos F165.
    """
    archivos = db.query(ArchivoExcel).filter(ArchivoExcel.activo == True).order_by(ArchivoExcel.fecha_creacion.desc().limit(limit=100)).all()

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
            "tamaño_mb": round(archivo.tamaño_bytes / 1024 / 1024, 2)  # Convertir a MB
        }
        for archivo in archivos
    ]