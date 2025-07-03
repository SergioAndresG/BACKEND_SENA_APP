from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from connection import base, crear
from EDNPOINTS.tokens import router_tokens

app = FastAPI(title="SENA - Procesador de Fichas")
app.include_router(router_tokens)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # URLs de Vue
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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