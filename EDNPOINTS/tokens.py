from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, APIRouter
from MODELS import Aprendiz, Ficha
from SCHEMAS.aprendiz_schemas import ExportarF165Request
from FUNCIONES import procesar_archivos_background
from connection import SessionLocal
from typing import List
import uuid
from fastapi.responses import FileResponse
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
import base64
from PIL import Image
import io
from io import BytesIO
from fastapi.responses import StreamingResponse
from tempfile import NamedTemporaryFile

router_tokens = APIRouter()


procesamiento_estado = {}

@router_tokens.post("/upload-fichas/")
async def upload_fichas(
    background_tasks: BackgroundTasks,
    archivos: List[UploadFile] = File(...)
):
    """
    Endpoint para recibir múltiples archivos Excel desde Vue.js
    """
    # Validar archivos
    if not archivos:
        raise HTTPException(status_code=400, detail="No se enviaron archivos")
    
    archivos_validos = []
    for archivo in archivos:
        if not archivo.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400, 
                detail=f"Archivo {archivo.filename} no es Excel válido"
            )
        
        # Leer contenido del archivo
        contenido = await archivo.read()
        archivos_validos.append((contenido, archivo.filename))
    
    # Generar ID único para esta tarea
    task_id = str(uuid.uuid4())
    
    # Iniciar procesamiento en background
    background_tasks.add_task(
        procesar_archivos_background, 
        task_id, 
        archivos_validos
    )
    
    return {
        "message": f"Procesamiento iniciado para {len(archivos_validos)} archivos",
        "task_id": task_id,
        "total_archivos": len(archivos_validos)
    }

@router_tokens.get("/status/{task_id}")
async def get_status(task_id: str):
    """
    Obtener estado del procesamiento
    """
    if task_id not in procesamiento_estado:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    estado = procesamiento_estado[task_id]
    
    # Calcular progreso
    progreso = (estado["archivos_procesados"] / estado["total_archivos"]) * 100
    
    return {
        "status": estado["status"],
        "progreso": round(progreso, 2),
        "archivos_procesados": estado["archivos_procesados"],
        "total_archivos": estado["total_archivos"],
        "resultados": estado["resultados"]
    }

@router_tokens.get("/fichas/")
async def listar_fichas():
    """
    Listar todas las fichas disponibles
    """
    session = SessionLocal()
    try:
        fichas = session.query(Ficha).all()
        resultado = []
        
        for ficha in fichas:
            total_aprendices = session.query(Aprendiz).filter(
                Aprendiz.ficha_numero == ficha.numero_ficha
            ).count()
            
            resultado.append({
                "numero_ficha": ficha.numero_ficha,
                "programa": ficha.programa,
                "estado": ficha.estado,
                "fecha_reporte": str(ficha.fecha_reporte) if ficha.fecha_reporte else None,
                "total_aprendices": total_aprendices
            })
        
        return {"fichas": resultado}
    
    finally:
        session.close()

@router_tokens.get("/ficha/{numero_ficha}/aprendices")
async def obtener_aprendices(numero_ficha: str):
    """
    Obtener aprendices de una ficha específica
    """
    session = SessionLocal()
    try:
        aprendices = session.query(Aprendiz).filter(
            Aprendiz.ficha_numero == numero_ficha
        ).all()
        
        if not aprendices:
            raise HTTPException(status_code=404, detail="Ficha no encontrada")
        
        resultado = []
        for aprendiz in aprendices:
            resultado.append({
                "id": aprendiz.id_aprendiz,
                "documento": aprendiz.documento,
                "nombre": aprendiz.nombre,
                "apellido": aprendiz.apellido,
                "celular": aprendiz.celular,
                "correo": aprendiz.correo,
                "estado": aprendiz.estado,
                "tipo_documento": aprendiz.tipo_documento
            })
        
        return {
            "numero_ficha": numero_ficha,
            "total_aprendices": len(resultado),
            "aprendices": resultado
        }
    
    finally:
        session.close()
        
@router_tokens.get("/ficha/{numero_ficha}/aprendiz")
async def obtener_aprendiz(numero_ficha: str, documento: str = None):
    """
    Obtener aprendiz de una ficha específica, filtrando por número de documento.
    """
    session = SessionLocal()
    try:
        query = session.query(Aprendiz).filter(Aprendiz.ficha_numero == numero_ficha)

        if documento:
            query = query.filter(Aprendiz.documento == documento)

        aprendices = query.all()

        if not aprendices:
            raise HTTPException(status_code=404, detail="Aprendiz o ficha no encontrados")
        
        resultado = [{
            "id": aprendiz.id_aprendiz,
            "documento": aprendiz.documento,
            "nombre": aprendiz.nombre,
            "apellido": aprendiz.apellido,
            "celular": aprendiz.celular,
            "correo": aprendiz.correo,
            "estado": aprendiz.estado,
            "tipo_documento": aprendiz.tipo_documento
        } for aprendiz in aprendices]

        return {
            "numero_ficha": numero_ficha,
            "total_aprendices": len(resultado),
            "aprendices": resultado
        }
    finally:
        session.close()

@router_tokens.post("/exportar-f165")
def exportar_f165(request: ExportarF165Request):
    modalidad = request.modalidad
    aprendices = request.aprendices

    print("Recibido:", aprendices)
    if not aprendices:
        raise HTTPException(status_code=400, detail="Lista de aprendices vacía")

    # Cargar el archivo base
    ruta_archivo = "GFPI-F-165V3FormatoSeleccionModificacionAlternativaparadesarrollarlaEtapaProductiva.xlsx"
    wb = load_workbook(ruta_archivo)

    # Selección de hoja según modalidad (aunque luego la eliminarás si es fija)
    if modalidad == "grupal":
        hoja = wb["Selección formato 1 - Grupal"]
    elif modalidad == "individual":
        hoja = wb["Selección Modificación F2 Indiv"]
    else:
        raise HTTPException(status_code=400, detail="Modalidad no válida")

    # Fila inicial donde comienzan los aprendices
    fila_inicial = 18
    espacios_disponibles = 20
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

        # Decodificar y guardar en archivo temporal
        firma_bytes = base64.b64decode(firma_data)
        with NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file.write(firma_bytes)
            tmp_file_path = tmp_file.name
            
        img = OpenpyxlImage(tmp_file_path)
        img.width = 80  # ajusta según tu formato
        img.height = 30

        # Supongamos que quieres insertar en la columna AG de la fila i
        celda_firma = f"AG{fila}"
        img.anchor = celda_firma

        hoja.add_image(img)

    # Guardar en memoria y retornar
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=formato_F165.xlsx"
        }
    )

