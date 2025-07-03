from connection import crear, get_db, base, SessionLocal
from MODELS import Ficha, Aprendiz
from datetime import datetime
from typing import List
import polars as pl
import tempfile
import os
import asyncio

class ProcesadorArchivos:
    def __init__(self):
        self.session = SessionLocal()
    
    def procesar_archivo_individual(self, archivo_bytes: bytes, nombre_archivo: str):
        """Procesa un archivo Excel individual"""
        try:
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                temp_file.write(archivo_bytes)
                temp_path = temp_file.name

            # ✅ CORREGIR: Leer archivo Excel sin parámetros no válidos
            # Nota: read_excel en versiones recientes de Polars no acepta read_csv_options
            df = pl.read_excel(temp_path)
            print("DataFrame completo shape:", df.shape)
            print("Primeras 6 filas:")
            print(df.head(6).to_pandas())

            # Verificar que tenemos suficientes filas
            if df.height < 5:
                raise ValueError(f"El archivo {nombre_archivo} no tiene suficientes filas. Se necesitan al menos 5 filas.")

            # Extraer cabecera (las 4 primeras filas)
            cabecera = df.slice(0, 4).to_numpy()
            print("Cabecera extraída:", cabecera)

            # ✅ CORREGIR: Obtener nombres de columna reales desde la fila 4 (índice 3) de la cabecera
            # Los nombres están en cabecera[3], no en df.row(4)
            nombres_columnas = [str(col).strip() for col in cabecera[3] if col is not None and str(col).strip() != '']
            
            print("Nombres de columnas extraídos:", nombres_columnas)

            # Validar que tenemos las columnas básicas necesarias
            columnas_requeridas = ["Tipo de Documento", "Número de Documento", "Nombre", "Apellidos"]
            columnas_faltantes = [col for col in columnas_requeridas if col not in nombres_columnas]
            
            if columnas_faltantes:
                print(f"⚠️  Columnas críticas faltantes: {columnas_faltantes}")
                print(f"⚠️  Columnas disponibles: {nombres_columnas}")
                # No lanzar error, continuar con las columnas disponibles
            else:
                print("✅ Todas las columnas requeridas están presentes")

            # Extraer datos desde la fila 6 (índice 5)
            df_datos = df.slice(5)
            
            print("✅ DataFrame de datos configurado:")
            print("   Shape original:", df_datos.shape)
            print("   Columnas originales:", df_datos.columns)

            # ✅ CORREGIR: Trabajar directamente con las columnas del DataFrame
            # Las columnas en df_datos corresponden a las posiciones en nombres_columnas
            
            # Verificar que tenemos suficientes columnas
            num_cols_necesarias = len(nombres_columnas)
            if df_datos.width < num_cols_necesarias:
                print(f"⚠️  Ajustando número de columnas de {num_cols_necesarias} a {df_datos.width}")
                nombres_columnas = nombres_columnas[:df_datos.width]
            
            # Seleccionar las primeras N columnas que corresponden a nuestros datos
            columnas_a_usar = df_datos.columns[:len(nombres_columnas)]
            df_datos = df_datos.select(columnas_a_usar)
            
            # Renombrar las columnas con los nombres correctos
            df_datos.columns = nombres_columnas
            
            print(f"✅ Columnas renombradas correctamente: {df_datos.columns}")

            print("   Columnas finales:", df_datos.columns)
            print("   Shape final:", df_datos.shape)
            if df_datos.height > 0:
                print("   Primera fila de datos:", dict(zip(df_datos.columns, df_datos.row(0))))

            # Procesar datos
            fichas_creadas, aprendices_creados = self._procesar_datos(df_datos, cabecera)

            # Eliminar archivo temporal
            os.unlink(temp_path)

            return {
                "archivo": nombre_archivo,
                "status": "success",
                "fichas_creadas": fichas_creadas,
                "aprendices_creados": aprendices_creados
            }
            
        except Exception as e:
            # Si existe el archivo temporal, eliminarlo
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            print(f"❌ Error procesando {nombre_archivo}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "archivo": nombre_archivo,
                "status": "error",
                "error": str(e)
            }

    def _procesar_datos(self, df: pl.DataFrame, cabecera: list):
        """Procesa y guarda datos en BD - SOLO POLARS"""
        fichas_creadas = 0
        aprendices_creados = 0

        try:
            # 🔍 DEBUG: Ver qué contiene la cabecera
            print("🔍 Cabecera completa:")
            for i, fila in enumerate(cabecera):
                print(f"   Fila {i}: {fila}")

            # ✅ EXTRAER METADATOS: Mejorar la extracción de datos de la cabecera
            numero_ficha = ""
            estado_ficha = ""
            fecha_reporte = None
            
            # Buscar información en todas las filas de la cabecera
            for i, fila in enumerate(cabecera):
                fila_str = " ".join([str(cell) for cell in fila if cell is not None])
                print(f"   Procesando fila {i}: {fila_str}")
                
                # Buscar número de ficha
                if "ficha" in fila_str.lower() and not numero_ficha:
                    # Buscar patrón de números en la cadena
                    import re
                    match = re.search(r'(\d{7})', fila_str)  # Buscar 7 dígitos
                    if match:
                        numero_ficha = match.group(1)
                        print(f"   ✅ Número de ficha encontrado: {numero_ficha}")
                
                # Buscar estado
                if "estado" in fila_str.lower() and not estado_ficha:
                    partes = fila_str.split(":")
                    if len(partes) > 1:
                        estado_ficha = partes[1].strip()
                        print(f"   ✅ Estado encontrado: {estado_ficha}")
                
                # Buscar fecha
                if "fecha" in fila_str.lower() and not fecha_reporte:
                    import re
                    # Buscar patrón de fecha DD/MM/YYYY
                    match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', fila_str)
                    if match:
                        fecha_str = match.group(1)
                        fecha_reporte = self._convertir_fecha(fecha_str)
                        print(f"   ✅ Fecha encontrada: {fecha_reporte}")

            print(f"📋 Metadatos extraídos:")
            print(f"   🔢 Número ficha: '{numero_ficha}'")
            print(f"   📊 Estado: '{estado_ficha}'") 
            print(f"   📅 Fecha: {fecha_reporte}")

            # ✅ VALIDAR: Que el número de ficha no esté vacío
            if not numero_ficha or numero_ficha.strip() == "":
                raise ValueError("❌ No se pudo extraer el número de ficha de la cabecera")

            # Crear o verificar ficha
            ficha_existente = self.session.query(Ficha).filter(Ficha.numero_ficha == numero_ficha).first()

            if not ficha_existente:
                nueva_ficha = Ficha(
                    numero_ficha=numero_ficha,
                    programa="CURSO INTRODUCTORIO A LA FORMACIÓN PROFESIONAL INTEGRAL",
                    estado=estado_ficha or "DESCONOCIDO",
                    fecha_reporte=fecha_reporte
                )
                self.session.add(nueva_ficha)
                fichas_creadas += 1
                print(f"✅ Nueva ficha creada: {numero_ficha}")

            # 🔥 POLARS: Mapear columnas a nombres estándar para la base de datos
            columnas_actuales = df.columns
            print(f"📊 Columnas actuales en DataFrame: {columnas_actuales}")
            
            # Mapeo directo de columnas
            mapeo_columnas = {}
            for col in columnas_actuales:
                col_lower = col.lower().replace(" ", "").replace("de", "").replace("ó", "o")
                if "tipodocumento" in col_lower:
                    mapeo_columnas[col] = "tipo_documento"
                elif "numerodocumento" in col_lower or "documento" in col_lower:
                    mapeo_columnas[col] = "documento"
                elif col_lower == "nombre":
                    mapeo_columnas[col] = "nombre"
                elif "apellido" in col_lower:
                    mapeo_columnas[col] = "apellido"
                elif "celular" in col_lower:
                    mapeo_columnas[col] = "celular"
                elif "correo" in col_lower or "email" in col_lower:
                    mapeo_columnas[col] = "correo"
                elif "estado" in col_lower or "estado" in col_lower:
                    mapeo_columnas[col] = "estado"
            
            print(f"📋 Mapeo de columnas: {mapeo_columnas}")
            
            # Renombrar solo las columnas que pudimos mapear
            if mapeo_columnas:
                df = df.rename(mapeo_columnas)
                print(f"✅ Columnas renombradas: {df.columns}")
            else:
                print("⚠️  No se pudo mapear ninguna columna, usando nombres originales")

            # 🔥 POLARS: Agregar columna de ficha
            df = df.with_columns([
                pl.lit(numero_ficha).alias("ficha_numero")
            ])

            print(f"📊 Procesando {df.height} filas de aprendices...")

            # 🔥 POLARS: Procesar datos fila por fila
            for i in range(df.height):
                try:
                    # Obtener la fila actual
                    fila = df.row(i, named=True)
                    
                    # Validar documento
                    documento_str = str(fila.get("documento", "")).strip() if fila.get("documento") is not None else ""
                    if not documento_str or documento_str in ["", "nan", "None", "null"]:
                        print(f"⚠️  Fila {i+1}: Saltando por documento vacío")
                        continue

                    # Verificar si ya existe
                    aprendiz_existente = self.session.query(Aprendiz).filter(
                        Aprendiz.documento == documento_str,
                        Aprendiz.ficha_numero == numero_ficha
                    ).first()

                    if not aprendiz_existente:
                        # ✅ CREAR APRENDIZ: Validación y limpieza de datos
                        nuevo_aprendiz = Aprendiz(
                            ficha_numero=numero_ficha,
                            tipo_documento=str(fila.get("tipo_documento", "CC")).strip(),
                            documento=documento_str,
                            nombre=str(fila.get("nombre", "")).strip(),
                            apellido=str(fila.get("apellido", "")).strip(),
                            celular=self._limpiar_campo(fila.get("celular")),
                            correo=self._limpiar_campo(fila.get("correo")),
                            estado=self._limpiar_campo(fila.get("estado"))
                        )
                        self.session.add(nuevo_aprendiz)
                        aprendices_creados += 1
                        
                        if aprendices_creados % 10 == 0:  # Log cada 10 aprendices
                            print(f"📝 Creados {aprendices_creados} aprendices...")
                            
                    else:
                        print(f"⚠️  Aprendiz {documento_str} ya existe en ficha {numero_ficha}")
                        
                except Exception as row_error:
                    print(f"❌ Error procesando fila {i+1}: {row_error}")
                    continue  # Continuar con la siguiente fila

            # ✅ COMMIT con manejo de errores
            try:
                self.session.commit()
                print(f"✅ Commit exitoso: {fichas_creadas} fichas, {aprendices_creados} aprendices creados")
                return fichas_creadas, aprendices_creados
            except Exception as commit_error:
                self.session.rollback()
                print(f"❌ Error en commit: {commit_error}")
                raise commit_error
                
        except Exception as e:
            self.session.rollback()
            print(f"❌ Error general en _procesar_datos: {str(e)}")
            import traceback
            traceback.print_exc()
            raise e
        
    def _limpiar_campo(self, valor):
        """Limpia un campo, devolviendo string vacío si es None o 'nan'"""
        if valor is None:
            return ""
        valor_str = str(valor).strip()
        if valor_str.lower() in ["nan", "none", "null", ""]:
            return ""
        return valor_str

    def _convertir_fecha(self, fecha_str):
        """Convierte fecha string a date"""
        if fecha_str:
            try:
                if isinstance(fecha_str, str):
                    return datetime.strptime(fecha_str, "%d/%m/%Y").date()
                return fecha_str
            except:
                return None
        return None
    