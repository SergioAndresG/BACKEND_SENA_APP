from connection import SessionLocal
from MODELS import FichaMaestro
from datetime import datetime
import polars as pl
import pandas as pd
import tempfile
import os

# PASO 3: Clase para procesar archivo maestro
class ProcesadorArchivoMaestro:
    def __init__(self):
        self.session = SessionLocal()
    
    def procesar_archivo_maestro(self, archivo_bytes: bytes, nombre_archivo: str):
        """Procesa el archivo maestro y actualiza la tabla FichasMaestro"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as temp_file:
                temp_file.write(archivo_bytes)
                temp_path = temp_file.name

            columnas = ["IDENTIFICADOR_FICHA", "FECHA_INICIO_FICHA", "FECHA_TERMINACION_FICHA"]
            df_pandas = pd.read_excel(temp_path, header=4, usecols=columnas)
            df = pl.from_pandas(df_pandas)

            print(f"📊 Archivo maestro cargado - Shape: {df.shape}")
            print(f"Columnas disponibles: {df.columns}")

            # Identificar columnas necesarias
            columnas_necesarias = self._identificar_columnas_maestro(df)
            
            if not columnas_necesarias:
                raise ValueError("No se pudieron identificar las columnas necesarias en el archivo maestro")

            df_limpio = df.select([
                "IDENTIFICADOR_FICHA",
                "FECHA_INICIO_FICHA",
                "FECHA_TERMINACION_FICHA"
            ]).rename({
                "IDENTIFICADOR_FICHA": "identificador_ficha",
                "FECHA_INICIO_FICHA": "fecha_inicio",
                "FECHA_TERMINACION_FICHA": "fecha_fin"
            })
            
            df_limpio = df_limpio.with_columns([
                pl.col("identificador_ficha").cast(pl.Utf8)
            ])

            df_limpio = df_limpio.filter(
                pl.col("identificador_ficha").is_not_null() &
                (pl.col("identificador_ficha") != "") &
                (pl.col("identificador_ficha") != "nan")
            )

            print(f"✅ Filas válidas a procesar: {df_limpio.height}")

            # Procesar cada fila
            fichas_actualizadas = 0
            fichas_creadas = 0
            fecha_actualizacion = datetime.now().date()

            for i in range(df_limpio.height):
                try:
                    fila = df_limpio.row(i, named=True)
                    
                    numero_ficha = str(fila['identificador_ficha']).strip()
                    fecha_inicio = self._convertir_fecha(fila['fecha_inicio'])
                    fecha_fin = self._convertir_fecha(fila['fecha_fin'])

                    # UPSERT en tabla maestro (Combinacion de Insertar y Actualizar)
                    ficha_maestro = self.session.query(FichaMaestro).filter(
                        FichaMaestro.numero_ficha == numero_ficha
                    ).first()

                    if ficha_maestro:
                        # Actualizar
                        ficha_maestro.fecha_inicio = fecha_inicio
                        ficha_maestro.fecha_fin = fecha_fin
                        ficha_maestro.fecha_actualizacion = fecha_actualizacion
                        fichas_actualizadas += 1
                    else:
                        # Crear
                        nueva_ficha_maestro = FichaMaestro(
                            numero_ficha=numero_ficha,
                            fecha_inicio=fecha_inicio,
                            fecha_fin=fecha_fin,
                            fecha_actualizacion=fecha_actualizacion
                        )
                        self.session.add(nueva_ficha_maestro)
                        fichas_creadas += 1

                    # Commit cada 100 registros
                    if (fichas_actualizadas + fichas_creadas) % 100 == 0:
                        self.session.commit()
                        print(f"📝 Procesadas {fichas_actualizadas + fichas_creadas} fichas maestro...")

                except Exception as row_error:
                    print(f"❌ Error procesando fila {i+1}: {row_error}")
                    continue

            # Commit final
            self.session.commit()
            os.unlink(temp_path)

            return {
                "archivo": nombre_archivo,
                "status": "success",
                "fichas_creadas": fichas_creadas,
                "fichas_actualizadas": fichas_actualizadas,
                "total_procesadas": fichas_creadas + fichas_actualizadas
            }

        except Exception as e:
            self.session.rollback()
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            print(f"❌ Error procesando archivo maestro: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "archivo": nombre_archivo,
                "status": "error",
                "error": str(e)
            }

    def _identificar_columnas_maestro(self, df: pl.DataFrame):
        """Identifica automáticamente las columnas del archivo maestro"""
        columnas = df.columns
        columnas_encontradas = {}
        
        for col in columnas:
            col_lower = col.lower().replace(" ", "").replace("_", "")
            
            # Buscar número de ficha
            if any(palabra in col_lower for palabra in ["ficha", "numero", "código", "codigo"]):
                if "numero" in col_lower and "ficha" in col_lower:
                    columnas_encontradas['numero_ficha'] = col
                elif not columnas_encontradas.get('numero_ficha'):
                    columnas_encontradas['numero_ficha'] = col
            
            # Buscar fecha inicio
            if any(palabra in col_lower for palabra in ["inicio", "inicioformacion", "fechainicio"]):
                columnas_encontradas['fecha_inicio'] = col
            
            # Buscar fecha fin
            if any(palabra in col_lower for palabra in ["fin", "finformacion", "fechafin", "terminacion"]):
                columnas_encontradas['fecha_fin'] = col

        print(f"🔍 Columnas identificadas: {columnas_encontradas}")
        
        if len(columnas_encontradas) == 3:
            return columnas_encontradas
        else:
            print(f"❌ Solo se encontraron {len(columnas_encontradas)} de 3 columnas necesarias")
            print(f"Columnas disponibles: {columnas}")
            return None

    def _convertir_fecha(self, fecha_valor):
        """Convierte diferentes formatos de fecha a date"""
        if fecha_valor is None:
            return None
            
        try:
            if hasattr(fecha_valor, 'date'):
                return fecha_valor.date()
            
            if isinstance(fecha_valor, str):
                fecha_str = fecha_valor.strip()
                if not fecha_str or fecha_str.lower() in ['nan', 'none', 'null']:
                    return None
                
                formatos = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"]
                for formato in formatos:
                    try:
                        return datetime.strptime(fecha_str, formato).date()
                    except:
                        continue
                        
            if isinstance(fecha_valor, (int, float)):
                from datetime import date, timedelta
                base_date = date(1900, 1, 1)
                return base_date + timedelta(days=int(fecha_valor) - 2)
                
        except Exception as e:
            print(f"Error convertiendo fecha {fecha_valor}: {e}")
            
        return None