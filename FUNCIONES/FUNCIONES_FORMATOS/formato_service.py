import uuid
import shutil
from pathlib import Path
from typing import Optional
import hashlib
from datetime import datetime
from MODELS.archivo_excel import ArchivoExcel
from connection import SessionLocal

class FormatoService:
    def __init__(self,base_path = "archivos_exportados"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def calcular_hash(self, ruta_archivo: Path) -> str:
        """Calcula el hash SHA256 de un archivo."""
        sha256 = hashlib.sha256() # Crea un objeto hash SHA256
        # Abre el archivo en modo binario y lee en bloques para evitar problemas de memoria
        with ruta_archivo.open(ruta_archivo, "rb") as f:
            # Lee el archivo en bloques de 8192 bytes
            # Esto es eficiente para archivos grandes
            while chunk := f.read(8192):
                # Actualiza el hash con el bloque leído
                sha256.update(chunk)
        # Devuelve el hash en formato hexadecimal
        return sha256.hexdigest()
    
    def generar_nombre_interno(self, extension:str="xlsx") -> str:
        """Genera un nombre interno único para el archivo."""
        timpestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        uuid_corto = str(uuid.uuid4())[:8]  # Genera un UUID y toma los primeros 8 caracteres
        return f"{uuid_corto}_{timpestamp}.{extension}"

    def obtener_ruta_organizada(self, nombre_interno:str) -> Path:
        """Oraganiza los archivos por año/mes para mejor gestion"""
        ahora = datetime.now()
        ruta = self.base_path / str(ahora.year) / str(ahora.month) / "exportados"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        return ruta / nombre_interno

    def guardar_archivo_seguro(self, contenido: bytes, nombre_original:str, 
                            ficha: str, modalidad: str, cantidad_aprendices:int,
                            usuario_id: Optional[int] = None) -> ArchivoExcel:
        """ Guarda un archivo de Excel de manera segura con validaciones """

        try:
            #Paso 1: generar nombres y rutas
            nombre_interno = self.generar_nombre_interno()
            ruta_completa = self.obtener_ruta_organizada(nombre_interno)
            ruta_relativa = ruta_completa.relative_to(self.base_path)

            #Paso 2: escribir el archivo
            with open(ruta_completa, "wb") as f:
                f.write(contenido)

            #Paso 3: calcular el hash y tamaño

            hash_archivo = self.calcular_hash(str(ruta_completa))
            tamaño_bytes = ruta_completa.stat().st_size

            #Paso 4: Crear registro en la base de datos
            archivo_db = ArchivoExcel(
                nombre_original=nombre_original,
                nombre_interno=nombre_interno,
                ruta_archivo=str(ruta_relativa),
                ficha=ficha,
                modalidad=modalidad,
                cantidad_aprendices=cantidad_aprendices,
                hash_archivo=hash_archivo,
                tamaño_bytes=tamaño_bytes,
                usuario_id=usuario_id if usuario_id else 0  # Asignar 0 si no se proporciona
            )
            return archivo_db
        except Exception as e:
            if ruta_completa.exists():
                ruta_completa.unlink()
            raise Exception(f"Error al guardar el archivo: {str(e)}") from e

    def verificar_integridad_archivo(self, archivo_db: ArchivoExcel) -> bool:
        """"Verifica que el archivo no este corrupto"""
        try:
            ruta_completa = self.base_path / archivo_db.ruta_archivo
            if not ruta_completa.exists():
                return False
            hash_calculado = self.calcular_hash(str(ruta_completa))
            return hash_calculado == archivo_db.hash_archivo
        except Exception:
            return False
        
    def obtene_archivo_para_descarga(self, archivo_db: ArchivoExcel) -> Path:
        """Obtiene la ruta completa del archivo para descarga"""
        try:
            ruta_completa = self.base_path / archivo_db.ruta_archivo

            if not self.verificar_integridad_archivo(archivo_db):
                raise FileNotFoundError(f"El archivo esta corrupto o no existe: {archivo_db.nombre_interno}")
            
            with open(ruta_completa, "rb") as f:
                contenido = f.read()
        
        except Exception as e:
            raise Exception(f"Error al leer el archivo: {str(e)}") from e
        

    def eliminar_archivo_seguro(self,archivo_db: ArchivoExcel) -> bool:
        """Eliminacion segura (soft delete)"""
        try:
            # 1. Soft delete en DB
            archivo_db.activo = False
            archivo_db.fecha_modificacion = datetime.now()
            SessionLocal.commit()  # Asumiendo que tienes una sesión de DB activa

            return True
        except Exception as e:
            SessionLocal.rollback()  # Revertir cambios en caso de error
            raise Exception(f"Error al eliminar el archivo: {str(e)}") from e
