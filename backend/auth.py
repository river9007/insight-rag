import os
import jwt
from jwt import PyJWKClient
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

# Ya no usamos SUPABASE_JWT_SECRET. Usamos la URL de tu proyecto para obtener las claves públicas.
SUPABASE_URL = "https://favkmokebzgekenbkffa.supabase.co"
jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"

# Cliente que descarga y gestiona las claves públicas de Supabase
jwks_client = PyJWKClient(jwks_url)
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        # 🛡️ MEJORA 1: Validamos la audiencia estrictamente
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256", "HS256"],
            audience="authenticated" # Requerimos explícitamente aud="authenticated"
        )
        
        # 🛡️ MEJORA 2: Verificamos el rol dentro del payload
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