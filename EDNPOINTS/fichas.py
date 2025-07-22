from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, APIRouter
from MODELS import Aprendiz, Ficha
from FUNCIONES import procesar_archivos_background, procesar_archivo_maestro_background
from connection import SessionLocal
from typing import List
import uuid

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

# NUEVO ENDPOINT PARA ARCHIVO MAESTRO MENSUAL
@router_tokens.post("/upload-archivo-maestro/")
async def upload_archivo_maestro(
    background_tasks: BackgroundTasks,
    archivo: UploadFile = File(...)
):
    """
    Endpoint para cargar el archivo maestro mensual
    🎯 Este es el que cargas una vez al mes
    """
    if not archivo.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail=f"Archivo {archivo.filename} no es Excel válido"
        )
    
    contenido = await archivo.read()
    task_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        procesar_archivo_maestro_background, 
        task_id, 
        (contenido, archivo.filename)
    )
    
    return {
        "message": f"📅 Archivo maestro mensual en procesamiento",
        "task_id": task_id,
        "archivo": archivo.filename,
        "tipo": "archivo_maestro",
        "nota": "🚀 Después de esto, las fichas nuevas tendrán fechas automáticamente"
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

        # Buscar la ficha
        ficha = session.query(Ficha).filter(Ficha.numero_ficha == numero_ficha).first()

        if not ficha:
            HTTPException(status_code=404, detail="La ficha no existe")

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
                "tipo_documento": aprendiz.tipo_documento,
                "estado": aprendiz.estado
            })
        
        return {
            "numero_ficha": numero_ficha,
            "total_aprendices": len(resultado),
            "fecha_inicio": ficha.fecha_inicio.isoformat() if ficha.fecha_inicio else None,
            "fecha_fin": ficha.fecha_fin.isoformat() if ficha.fecha_inicio else None,
            "aprendices": resultado
        }
    
    finally:
        session.close()