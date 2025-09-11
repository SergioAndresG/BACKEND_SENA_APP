from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from connection import base, crear
from ENDPOINTS.fichas import router_tokens
from ENDPOINTS.formatos import router_format
from ENDPOINTS.aprendices import router_aprendices
from ENDPOINTS.login import router_login
from ENDPOINTS.usuarios import router_usuarios

from MODELS.a_usuarios import Usuarios
from MODELS.archivo_excel import ArchivoExcel


from MIDELWARE.security_middleware import SecurityMiddleware

app = FastAPI(title="SENA - Procesador de Fichas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # URLs de Vue
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_tokens)
app.include_router(router_format)
app.include_router(router_aprendices)
app.include_router(router_login)
app.include_router(router_usuarios)


# Agregar middleware de seguridad
app.add_middleware(SecurityMiddleware, max_requests_per_minute=100)


base.metadata.create_all(bind=crear)

@app.on_event("startup")
async def startup():
    print("🚀 FastAPI iniciado")
    print("📁 Endpoints disponibles:")
    print("   POST /upload-fichas/ - Subir archivos Excel")
    print("   GET /status/{task_id} - Ver progreso")
    print("   GET /fichas/ - Listar fichas")
    print("   GET /ficha/{numero}/aprendices - Ver aprendices")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)