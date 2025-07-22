
"""
Script de prueba para simular el frontend
Sube archivos Excel a FastAPI y monitorea el progreso
"""

import requests
import time
import os
from pathlib import Path

class TestClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def subir_archivo_maestro(self, ruta_archivo):
        """Sube el archivo maestro mensual al servidor"""
        print(f"📅 Subiendo archivo maestro: {ruta_archivo}")
        
        if not os.path.exists(ruta_archivo):
            print(f"❌ Archivo maestro no encontrado: {ruta_archivo}")
            return None
        
        try:
            with open(ruta_archivo, 'rb') as archivo:
                files = {'archivo': (os.path.basename(ruta_archivo), archivo, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                
                response = requests.post(f"{self.base_url}/upload-archivo-maestro/", files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Archivo maestro subido exitosamente!")
                    print(f"   📊 Task ID: {data['task_id']}")
                    return data['task_id']
                else:
                    print(f"❌ Error subiendo archivo maestro: {response.text}")
                    return None
                
        except requests.exceptions.ConnectionError:
            print("❌ No se pudo conectar al servidor. ¿Está ejecutándose FastAPI?")
            return None
    
    def verificar_archivo_maestro(self):
        """Verifica si ya existe un archivo maestro cargado"""
        try:
            response = requests.get(f"{self.base_url}/archivo-maestro/status")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('existe', False):
                    print(f"✅ Archivo maestro ya existe (cargado: {data.get('fecha_carga', 'N/A')})")
                    return True
                else:
                    print("⚠️  No hay archivo maestro cargado")
                    return False
            else:
                print("⚠️  No se pudo verificar el archivo maestro")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ No se pudo conectar al servidor")
            return False
    
    def subir_archivos(self, rutas_archivos):
        """Sube múltiples archivos Excel al servidor"""
        print(f"📤 Subiendo {len(rutas_archivos)} archivos...")
        
        files = []
        for ruta in rutas_archivos:
            if os.path.exists(ruta):
                files.append(
                    ('archivos', (os.path.basename(ruta), open(ruta, 'rb'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
                )
            else:
                print(f"❌ Archivo no encontrado: {ruta}")
                return None
        
        try:
            response = requests.post(f"{self.base_url}/upload-fichas/", files=files)
            
            # Cerrar archivos
            for _, file_tuple in files:
                file_tuple[1].close()
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Subida exitosa!")
                print(f"   📊 Task ID: {data['task_id']}")
                print(f"   📁 Archivos procesando: {data['total_archivos']}")
                return data['task_id']
            else:
                print(f"❌ Error subiendo archivos: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            print("❌ No se pudo conectar al servidor. ¿Está ejecutándose FastAPI?")
            return None
    
    def monitorear_progreso(self, task_id):
        """Monitorea el progreso del procesamiento"""
        print(f"\n🔍 Monitoreando progreso de tarea: {task_id}")
        print("-" * 50)
        
        while True:
            try:
                response = requests.get(f"{self.base_url}/status/{task_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    print(f"\r📊 Progreso: {data['progreso']:.1f}% "
                          f"({data['archivos_procesados']}/{data['total_archivos']}) "
                          f"- Estado: {data['status']}", end="")
                    
                    if data['status'] == 'completed':
                        print("\n✅ Procesamiento completado!")
                        return data['resultados']
                    
                    time.sleep(2)  # Esperar 2 segundos antes de la siguiente consulta
                
                else:
                    print(f"\n❌ Error obteniendo estado: {response.text}")
                    break
                    
            except KeyboardInterrupt:
                print("\n⏹️ Monitoreo cancelado por el usuario")
                break
            except requests.exceptions.ConnectionError:
                print("\n❌ Conexión perdida con el servidor")
                break
    
    def listar_fichas(self):
        """Lista todas las fichas disponibles"""
        try:
            response = requests.get(f"{self.base_url}/fichas/")
            
            if response.status_code == 200:
                data = response.json()
                fichas = data['fichas']
                
                print(f"\n📋 Fichas disponibles ({len(fichas)}):")
                print("-" * 80)
                
                for ficha in fichas:
                    print(f"🔸 Ficha: {ficha['numero_ficha']}")
                    print(f"   Estado: {ficha['estado']}")
                    print(f"   Aprendices: {ficha['total_aprendices']}")
                    print(f"   Fecha: {ficha['fecha_reporte']}")
                    print()
                
                return fichas
            else:
                print(f"❌ Error listando fichas: {response.text}")
                return []
                
        except requests.exceptions.ConnectionError:
            print("❌ No se pudo conectar al servidor")
            return []
    
    def ver_aprendices(self, numero_ficha):
        """Ver aprendices de una ficha específica"""
        try:
            response = requests.get(f"{self.base_url}/ficha/{numero_ficha}/aprendices")
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n👥 Aprendices de la ficha {numero_ficha}:")
                print(f"Total: {data['total_aprendices']}")
                print("-" * 80)
                
                for aprendiz in data['aprendices'][:5]:  # Mostrar solo 5
                    print(f"• {aprendiz['nombre']} {aprendiz['apellido']}")
                    print(f"  Doc: {aprendiz['documento']} | Tel: {aprendiz['celular']}")
                    print(f"  Email: {aprendiz['correo']}")
                    print()
                
                if len(data['aprendices']) > 5:
                    print(f"... y {len(data['aprendices']) - 5} más")
                
                return data['aprendices']
            else:
                print(f"❌ Error: {response.text}")
                return []
                
        except requests.exceptions.ConnectionError:
            print("❌ No se pudo conectar al servidor")
            return []

def main():
    """Función principal de prueba"""
    print("🧪 Cliente de prueba para FastAPI - SENA")

    print("=" * 50)
    
    client = TestClient()


    archivo_maestro = 'PE-04_1 a junio 2025.xlsx'

    print("\n📅 PASO 1: Verificando archivo maestro...")
    if not client.verificar_archivo_maestro():
        print("🚀 Cargando archivo maestro...")
        task_id_maestro = client.subir_archivo_maestro(archivo_maestro)
        
        if task_id_maestro:
            print("⏳ Esperando que termine el archivo maestro...")
            client.monitorear_progreso(task_id_maestro)
        else:
            print("❌ No se pudo cargar el archivo maestro")
            return
    
    # 1. Configurar archivos de prueba
    print("\n📚 PASO 2: Procesando archivos de fichas...")
    archivos_test = [
        "Reporte-de-Aprendices-Ficha-3147272.xlsx",
        "Reporte-de-Aprendices-Ficha-3147190.xlsx",
    ]
 
    for archivo in archivos_test:
        print(archivo, "=>", os.path.exists(archivo))  

    # Filtrar solo archivos existentes
    archivos_existentes = [f for f in archivos_test if os.path.exists(f)]
   
    
    if not archivos_existentes:
        print("❌ No se encontraron archivos Excel para probar")
        print("📝 Coloca archivos .xlsx en la misma carpeta del script")
        print("   Nombres sugeridos: reporte_aprendices_1.xlsx, reporte_aprendices_2.xlsx")
        return
    
    print(f"📁 Archivos encontrados: {archivos_existentes}")
    
    # 2. Subir archivos
    task_id = client.subir_archivos(archivos_existentes)
    
    if not task_id:
        return
    
    # 3. Monitorear progreso
    resultados = client.monitorear_progreso(task_id)
    
    if resultados:
        print("\n📊 Resultados del procesamiento:")
        print("-" * 50)
        
        for resultado in resultados:
            status_emoji = "✅" if resultado['status'] == 'success' else "❌"
            print(f"{status_emoji} {resultado['archivo']}")
            
            if resultado['status'] == 'success':
                print(f"   Fichas: {resultado['fichas_creadas']}")
                print(f"   Aprendices: {resultado['aprendices_creados']}")
            else:
                print(f"   Error: {resultado['error']}")
            print()
    
    # 4. Listar fichas
    fichas = client.listar_fichas()
    
    # 5. Ver aprendices de la primera ficha
    if fichas:
        primera_ficha = fichas[0]['numero_ficha']
        client.ver_aprendices(primera_ficha)

if __name__ == "__main__":
    main()