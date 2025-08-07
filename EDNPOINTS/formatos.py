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

router_format = APIRouter()

format_service = FormatoService()

UPLOAD_DIR = "archivos_exportados"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


@router_format.post("/exportar-f165")
async def exportar_f165(request: ExportarF165Request, db: Session = Depends(get_db)):

    ficha = db.query(Ficha).filter(Ficha.numero_ficha == request.ficha).first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
        

    #1. Validaciones
    if not request.aprendices:
        raise HTTPException(status_code=400, detail="Lista de aprendices vacía")

    modalidad = request.modalidad # 'grupal' o 'individual'
    aprendices = request.aprendices # Lista de aprendices a exportar
    usuario_gene = request.usuario_generator # Usuario que genera el archivo


    usuario = db.query(Usuarios).filter(
        Usuarios.nombre == usuario_gene.nombre, 
        Usuarios.apellidos == usuario_gene.apellidos
    ).first()


    if not usuario:
        usuario = Usuarios(
        nombre=usuario_gene.nombre,
        apellidos=usuario_gene.apellidos,
        correo=usuario_gene.correo,
        rol=usuario_gene.rol,
        contraseña="123"
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)


    else:
        # Si no existe, continuar con la generación del archivo
        pass

    # Procesamiento asincrono de imagenes
    async def procesar_imagen(firma_data:str)-> str:
        try:
            #Eliminar encabezado si existe
            if "," in firma_data:
                firma_data = firma_data.split(",")[1]
            # Decadificar base64
            firma_bytes = base64.b64decode(firma_data)

            #Crear un archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
                tmp_file.write(firma_bytes)
                return tmp_file.name
        except Exception as e:
            print(f"Errrp procesando imagen: {e}")
            return None
    
    # Procesar las firmas en paralelo
    executor = ThreadPoolExecutor(max_workers=4)
    tareas_imagenes = []

    for ap in aprendices:
        if ap.firma:
            tarea = asyncio.get_event_loop().run_in_executor(
                executor,
                lambda firma=ap.firma: asyncio.run(procesar_imagen(firma))
            )
            tareas_imagenes.append(tarea)
        else:
            tareas_imagenes.append(asyncio.create_task(asyncio.sleep(0, result=None)))  # Placeholder para aprendices sin firma

    imagenes_procesadas = await asyncio.gather(*tareas_imagenes)

    # Cargar el archivo base
    ruta_archivo = "GFPI-F-165V3FormatoSeleccionModificacionAlternativaparadesarrollarlaEtapaProductiva.xlsx"
    try:
        wb = load_workbook(ruta_archivo) # Cargar el archivo de Excel .xlsx
    except FileNotFoundError:
        raise HTTPException(status_code=404,detail="Archivo no encontrado")

    # Selección de hoja según modalidad
    if modalidad == "grupal":
        hoja = wb["Selección formato 1 - Grupal"]
    elif modalidad == "individual":
        hoja = wb["Selección Modificación F2 Indiv"]
    else:
        raise HTTPException(status_code=400, detail="Modalidad no válida")
    
    fecha_inicio = ficha.fecha_inicio.strftime("%d-%m-%Y") if ficha.fecha_inicio else "N/A"
    fecha_fin = ficha.fecha_fin.strftime("%d-%m-%Y") if ficha.fecha_fin else "N/A"

    fecha_actual = datetime.now().strftime("%d-%m-%Y")

    datos_fechas = {
        "E13": fecha_inicio,
        "H13": fecha_fin,
        "H14": fecha_fin, 
        "E11": fecha_actual
    }

    # Aplicar todo de una vez
    font_style = Font(size=12, bold=True)
    for celda, valor in datos_fechas.items():
        hoja[celda] = valor
        hoja[celda].font = font_style
    hoja["T11"] = request.ficha  # Número de ficha

    nombre_completo_instructor = f"{usuario.nombre} {usuario.apellidos}"

    correo_instructor = usuario.correo
    
    if modalidad == "grupal":
        hoja["T13"] = nombre_completo_instructor  # Instructor
        hoja["T14"] = correo_instructor  # Correo



    fila_inicial = 18 # Los datos empiezan en la fila 18
    espacios_disponibles = 20 # La plantilla tiene 20 espacios
    aprendices_extra = len(aprendices) - espacios_disponibles

    # Inserta filas si hay más aprendices que espacios
    if aprendices_extra > 0:
        hoja.insert_rows(idx=fila_inicial + espacios_disponibles, amount=aprendices_extra)

    # Llenar datos de forma optimizada
    for i, (ap, imagen_path) in enumerate(zip(aprendices, imagenes_procesadas)):
        fila = fila_inicial + i
        
        # Escribir todos los datos de texto de una vez
        datos_fila = [
            (f"C{fila}", ap.tipo_documento),
            (f"D{fila}", ap.documento),
            (f"E{fila}", ap.nombre),
            (f"F{fila}", ap.apellido),
            (f"G{fila}", ap.direccion),
            (f"H{fila}", ap.correo),
            (f"I{fila}", ap.celular),
            (f"L{fila}", ap.tipo_discapacidad),
            (f"M{fila}", "x")
        ]
        
        for celda, valor in datos_fila:
            hoja[celda] = valor
        
        # Manejar discapacidad
        if ap.discapacidad == 'No':
            hoja[f"K{fila}"] = "x"
        else:
            hoja[f"J{fila}"] = "x"
        
        # Insertar imagen si se procesó correctamente
        if imagen_path:
            try:
                img = OpenpyxlImage(imagen_path)
                img.width = 80
                img.height = 30
                img.anchor = f"AG{fila}"
                hoja.add_image(img)
            except Exception as e:
                print(f"Error insertando imagen en fila {fila}: {e}")

    # Generar archivo con nombre optimizado
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_original = f"F165_{modalidad}_{request.ficha}_{timestamp}.xlsx"
    nombre_interno = f"F165_{usuario.id}_{timestamp}_{request.ficha}.xlsx"
    ruta_completa = os.path.join(UPLOAD_DIR, nombre_interno)

    wb.save(ruta_completa)
    wb.close() # Cerrar el waokbook para liberar memoria

    # Calcular hashd del archivo
    with open(ruta_completa, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    tamaño_archivo = os.path.getsize(ruta_completa)

    # Limpiar archivos temporales
    for imagen_path in imagenes_procesadas:
        if imagen_path and os.path.exists(imagen_path):
            try:
                os.unlink(imagen_path)
            except Exception as e:
                print(f"Error eliminando archivo temporal: {e}")

    # Calcular hash y guardar en BD (OPTIMIZADO)
    try:
        with open(ruta_completa, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        tamaño_archivo = os.path.getsize(ruta_completa)


        # Guardar en la base de datos
        archivo_excel = ArchivoExcel(
            nombre_original=nombre_original,
            nombre_interno=nombre_interno,
            ruta_archivo=ruta_completa,
            ficha=request.ficha,
            modalidad=modalidad,
            cantidad_aprendices=len(aprendices),
            hash_archivo=file_hash,
            tamaño_bytes=tamaño_archivo,
            usuario_id=usuario.id
        )

        db.add(archivo_excel)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=404,detail=f"Error al guardar en la base de datos: {e}")




    #Retornar archivo, optimizado
    try:
        # Usar FileResponse en lugar de StreamingREsponse para archivos mas grandes
        return FileResponse(
            path=ruta_completa,
            filename=nombre_original,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando archivo: {str(e)}")


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