from FUNCIONES import ProcesadorArchivoMaestro

# Almacenar estado de procesamiento
procesamiento_estado = {}
# Función para procesar archivo maestro en background
def procesar_archivo_maestro_background(task_id: str, archivo_info: tuple):
    """Procesa el archivo maestro en segundo plano"""
    try:
        procesamiento_estado[task_id] = {
            "status": "processing",
            "archivo": archivo_info[1],
            "mensaje": "Procesando archivo maestro..."
        }
        
        procesador = ProcesadorArchivoMaestro()
        resultado = procesador.procesar_archivo_maestro(archivo_info[0], archivo_info[1])
        
        procesamiento_estado[task_id] = {
            "status": "completed",
            "archivo": archivo_info[1],
            "resultado": resultado,
            "mensaje": f"Procesamiento completado: {resultado['fichas_creadas']} fichas creadas, {resultado['fichas_actualizadas']} actualizadas"
        }
        
    except Exception as e:
        procesamiento_estado[task_id] = {
            "status": "error",
            "archivo": archivo_info[1],
            "error": str(e),
            "mensaje": f"Error procesando archivo maestro: {str(e)}"
        }