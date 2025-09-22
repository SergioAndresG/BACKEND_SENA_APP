# security_middleware.py
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import json
import hashlib
import secrets
from collections import defaultdict
from datetime import datetime, timedelta
import logging
import re
from typing import Dict, List
import ipaddress

# Configurar logging de seguridad
security_logger = logging.getLogger("security")
handler = logging.FileHandler("security.log")
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
security_logger.addHandler(handler)
security_logger.setLevel(logging.INFO)

# Rate limiting storage (en producción usar Redis)
rate_limit_storage = defaultdict(list)
blocked_ips = defaultdict(float)

# Lista de IPs sospechosas (en producción, usar base de datos)
SUSPICIOUS_IPS = set()
BLOCKED_USER_AGENTS = [
    'sqlmap', 'nikto', 'nessus', 'openvas', 'nmap', 'masscan',
    'zgrab', 'shodan', 'censys', 'python-requests/1.', 'curl/7.1'
]

# Patrones de ataque comunes
ATTACK_PATTERNS = [
    r'(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)',
    r'(?i)(script|javascript|vbscript|onload|onerror)',
    r'(?i)(<|>|&lt;|&gt;|%3c|%3e)',
    r'(?i)(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\\)',
    r'(?i)(\/etc\/passwd|\/etc\/shadow|boot\.ini|win\.ini)',
    r'(?i)(cmd\.exe|powershell|bash|sh\s)',
]

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests_per_minute: int = 60):
        super().__init__(app)
        self.max_requests_per_minute = max_requests_per_minute
        
    async def dispatch(self, request: Request, call_next):
        # Obtener información del cliente
        client_ip = self.get_client_ip(request)
        user_agent = request.headers.get("user-agent", "").lower()
        
        # 1. Verificar IP bloqueada
        if self.is_ip_blocked(client_ip):
            security_logger.warning(f"Blocked IP attempted access: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="IP temporalmente bloqueada"
            )
        
        # 2. Verificar User-Agent sospechoso
        if self.is_suspicious_user_agent(user_agent):
            security_logger.warning(f"Suspicious user agent from {client_ip}: {user_agent}")
            self.block_ip_temporary(client_ip, 3600)  # 1 hora
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado"
            )
        
        # 3. Rate limiting
        if not self.check_rate_limit(client_ip):
            security_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Demasiadas solicitudes"
            )
        
        # 4. Verificar tamaño del body
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            # Aumentamos el límite a 10MB para permitir archivos Excel
            if content_length and int(content_length) > 50 * 1024 * 1024:  # 10MB
                security_logger.warning(f"Large request body from {client_ip}: {content_length}")
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Payload demasiado grande"
                )
        
        # 5. Verificar headers de seguridad
        self.validate_security_headers(request)
        
        # Continuar con la solicitud
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # 6. Agregar headers de seguridad a la respuesta
        response = self.add_security_headers(response)
        
        # 7. Log de la solicitud
        security_logger.info(
            f"Request: {client_ip} - {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        
        return response
    
    def get_client_ip(self, request: Request) -> str:
        """Obtener la IP real del cliente"""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Verificar si la IP está bloqueada"""
        if ip in blocked_ips:
            return time.time() < blocked_ips[ip]
        return ip in SUSPICIOUS_IPS
    
    def block_ip_temporary(self, ip: str, duration: int):
        """Bloquear IP temporalmente"""
        blocked_ips[ip] = time.time() + duration
        security_logger.warning(f"IP {ip} blocked for {duration} seconds")
    
    def is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Verificar si el User-Agent es sospechoso"""
        for blocked_agent in BLOCKED_USER_AGENTS:
            if blocked_agent in user_agent:
                return True
        return False
    
    def check_rate_limit(self, ip: str) -> bool:
        """Verificar límite de velocidad"""
        now = time.time()
        minute_ago = now - 60
        
        # Limpiar solicitudes antiguas
        rate_limit_storage[ip] = [
            timestamp for timestamp in rate_limit_storage[ip] 
            if timestamp > minute_ago
        ]
        
        # Verificar límite
        if len(rate_limit_storage[ip]) >= self.max_requests_per_minute:
            return False
        
        # Agregar solicitud actual
        rate_limit_storage[ip].append(now)
        return True
    
    def validate_security_headers(self, request: Request):
        """Validar headers de seguridad"""
        # Verificar Content-Type para requests POST
        if request.method in ["POST", "PUT", "PATCH"]:
            # Si la solicitud no tiene cuerpo (ej. un POST sin datos), no es necesario validar Content-Type.
            content_length = request.headers.get("content-length")
            if not content_length or int(content_length) == 0:
                return

            content_type = request.headers.get("content-type", "")

            # Permitir multipart/form-data para subidas de archivo
            if content_type.startswith("multipart/form-data"):
                return

            # Mantener la validación para otros tipos de contenido
            if not content_type.startswith(("application/json", "application/x-www-form-urlencoded", "params")):
                security_logger.warning(f"Invalid content type: {content_type}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Content-Type no válido"
                )
    
    def add_security_headers(self, response: Response) -> Response:
        """Agregar headers de seguridad a la respuesta"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Permitted-Cross-Domain-Policies": "none"
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response

class InputSanitizer:
    """Clase para sanitizar y validar entradas"""
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 255) -> str:
        """Sanitizar string de entrada"""
        if not input_str:
            return ""
        
        # Truncar longitud
        sanitized = input_str[:max_length]
        
        # Remover caracteres peligrosos
        sanitized = re.sub(r'[<>"\';()&+]', '', sanitized)
        
        # Verificar patrones de ataque
        for pattern in ATTACK_PATTERNS:
            if re.search(pattern, sanitized):
                security_logger.warning(f"Attack pattern detected: {sanitized}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Entrada contiene contenido no válido"
                )
        
        return sanitized.strip()
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validar y sanitizar email"""
        if not email:
            raise ValueError("Email requerido")
        
        email = email.lower().strip()
        
        # Patrón de email simple pero seguro
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Formato de email inválido")
        
        # Verificar longitud
        if len(email) > 320:  # RFC 5321
            raise ValueError("Email demasiado largo")
        
        # Verificar dominios sospechosos
        suspicious_domains = ['temp-mail.org', '10minutemail.com', 'guerrillamail.com']
        domain = email.split('@')[1]
        if domain in suspicious_domains:
            raise ValueError("Dominio de email no permitido")
        
        return email
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, any]:
        """Validar fortaleza de contraseña"""
        issues = []
        score = 0
        
        if len(password) < 8:
            issues.append("Debe tener al menos 8 caracteres")
        else:
            score += 1
        
        if not re.search(r'[A-Z]', password):
            issues.append("Debe contener al menos una letra mayúscula")
        else:
            score += 1
        
        if not re.search(r'[a-z]', password):
            issues.append("Debe contener al menos una letra minúscula")
        else:
            score += 1
        
        if not re.search(r'\d', password):
            issues.append("Debe contener al menos un número")
        else:
            score += 1
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_-]', password):
            issues.append("Debe contener al menos un carácter especial")
        else:
            score += 1
        
        # Verificar patrones comunes débiles
        common_patterns = [
            r'123456', r'password', r'qwerty', r'admin', r'letmein',
            r'welcome', r'monkey', r'dragon'
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                issues.append("No use contraseñas comunes")
                score -= 1
                break
        
        return {
            "is_valid": len(issues) == 0,
            "score": max(0, score),
            "issues": issues
        }

class CSRFProtection:
    """Protección CSRF"""
    
    def __init__(self):
        self.tokens = {}  # En producción usar Redis
    
    def generate_token(self, user_id: str) -> str:
        """Generar token CSRF"""
        token = secrets.token_urlsafe(32)
        self.tokens[token] = {
            "user_id": user_id,
            "expires": datetime.now() + timedelta(hours=2)
        }
        return token
    
    def validate_token(self, token: str, user_id: str) -> bool:
        """Validar token CSRF"""
        if token not in self.tokens:
            return False
        
        token_data = self.tokens[token]
        
        if token_data["expires"] < datetime.now():
            del self.tokens[token]
            return False
        
        if token_data["user_id"] != user_id:
            return False
        
        return True
    
    def cleanup_expired_tokens(self):
        """Limpiar tokens expirados"""
        now = datetime.now()
        expired_tokens = [
            token for token, data in self.tokens.items()
            if data["expires"] < now
        ]
        
        for token in expired_tokens:
            del self.tokens[token]

# Instancia global de protección CSRF
csrf_protection = CSRFProtection()

# Función para usar en las rutas
def get_csrf_token(user_id: str) -> str:
    """Obtener token CSRF para un usuario"""
    return csrf_protection.generate_token(user_id)

def verify_csrf_token(token: str, user_id: str) -> bool:
    """Verificar token CSRF"""
    return csrf_protection.validate_token(token, user_id)

# Decorator para rutas protegidas con CSRF
def csrf_required(f):
    """Decorator para requerir validación CSRF"""
    def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if not request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Request object required"
            )
        
        csrf_token = request.headers.get('X-CSRF-Token')
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token required"
            )
        
        # Aquí necesitarías obtener el user_id del token JWT
        # user_id = get_user_id_from_jwt(request)
        # if not verify_csrf_token(csrf_token, user_id):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Invalid CSRF token"
        #     )
        
        return f(*args, **kwargs)
    return wrapper

# Utilidades adicionales de seguridad
def hash_ip_for_logging(ip: str) -> str:
    """Hash de IP para logging (GDPR compliance)"""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

def is_private_ip(ip: str) -> bool:
    """Verificar si es IP privada"""
    try:
        return ipaddress.ip_address(ip).is_private
    except:
        return False

def detect_tor_exit_node(ip: str) -> bool:
    """Detectar nodos de salida Tor (implementación básica)"""
    # En producción, usar una lista actualizada de nodos Tor
    # o un servicio como TorDNSEL
    return False