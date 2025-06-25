from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from connection import crear, get_db, base  
from MODELS.aprendices import Aprendiz
from MODELS.ficha import Ficha
from MODELS.usuarios import Usuarios

"""
add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # URL de tu frontend
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)
"""

app = FastAPI() 


base.metadata.create_all(bind=crear)

@app.get("/")
def leer():
    return {"mensaje": "Hola, FastAPI"}