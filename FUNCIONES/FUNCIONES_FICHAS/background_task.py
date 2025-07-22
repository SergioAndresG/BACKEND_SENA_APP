from FUNCIONES import ProcesadorArchivos, ProcesadorArchivoMaestro
from datetime import datetime
from typing import List
import asyncio


# Almacenar estado de procesamiento
procesamiento_estado = {}

# Función para procesar en background
async def procesar_archivos_background(task_id: str, archivos: List[tuple]):
    """Procesa archivos en segundo plano"""
    procesamiento_estado[task_id] = {
        "status": "processing",
        "total_archivos": len(archivos),
        "archivos_procesados": 0,
        "resultados": [],
        "inicio": datetime.now()
    }
    
    procesador = ProcesadorArchivos()
    
    for i, (archivo_bytes, nombre_archivo) in enumerate(archivos):
        try:
            # Procesar archivo individual
            resultado = procesador.procesar_archivo_individual(archivo_bytes, nombre_archivo)
            
            # Actualizar estado
            procesamiento_estado[task_id]["archivos_procesados"] = i + 1
            procesamiento_estado[task_id]["resultados"].append(resultado)
            
            print(f"✅ Archivo {i+1}/{len(archivos)} procesado: {nombre_archivo}")
            
        except Exception as e:
            print(f"❌ Error procesando archivo {nombre_archivo}: {str(e)}")
            procesamiento_estado[task_id]["resultados"].append({
                "archivo": nombre_archivo,
                "status": "error", 
                "error": str(e)
            })
        
        # Pequeña pausa para no sobrecargar
        await asyncio.sleep(0.1)
    
    # Marcar como completado
    procesamiento_estado[task_id]["status"] = "completed"
    procesamiento_estado[task_id]["fin"] = datetime.now()
    
    # Cerrar sesión del procesador
    procesador.session.close()