from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Definimos una URL con la cual vamos a ingresar a la base de datos
URL_DB = "mysql+mysqlconnector://root:larata420@localhost:3306/SENA"

# Creamos el motor de la base de datos con la URL utilizada
crear = create_engine(URL_DB)

# Configuramos la sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=crear)

# Creamos la clase base para los modelos
base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()