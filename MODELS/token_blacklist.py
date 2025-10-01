from sqlalchemy import Column, String, DateTime
from connection import base

class TokenBlacklist(base):
    __tablename__ = 'token_blacklist'
    
    # Usaremos el 'jti' (JWT ID) como identificador único del token.
    jti = Column(String(36), primary_key=True, index=True)
    
    # Guardamos cuándo expira para poder limpiar la tabla periódicamente.
    expires_at = Column(DateTime, nullable=False)
