# Archivo: backend/login_supabase.py
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar las variables de entorno (SUPABASE_URL y SUPABASE_ANON_KEY / SUPABASE_KEY)
load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("Error: Faltan las credenciales de Supabase en el archivo .env")
    exit()

supabase: Client = create_client(supabase_url, supabase_key)

# Reemplaza con las credenciales del usuario que creaste en Supabase
email = "admin@insightrag.com"
password = "Prueba1234!"

try:
    print("Conectando con Supabase para obtener el token...")
    respuesta = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    
    print("\n✅ --- TU TOKEN REAL DE SUPABASE --- ✅\n")
    print(respuesta.session.access_token)
    print("\n---------------------------------------\n")
except Exception as e:
    print(f"❌ Error al iniciar sesión: {e}")