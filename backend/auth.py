# Archivo: backend/auth.py
import os
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL no está configurada en el .env")

jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(jwks_url)
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256", "HS256"],
            audience="authenticated",
            leeway=10  # 👈 Tolerancia de 10 segundos para el margen iat/nbf
        )

        if payload.get("role") != "authenticated":
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado. Se requiere rol autenticado."
            )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token de autenticación inválido: {str(e)}")