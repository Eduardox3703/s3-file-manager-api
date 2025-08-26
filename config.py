import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno desde archivo .env
load_dotenv()

# Configuración común AWS
def get_required_env(key, description=""):
    """Obtiene una variable de entorno requerida o termina el programa"""
    value = os.getenv(key)
    if not value:
        print(f"Error: Variable de entorno {key} es requerida {description}")
        sys.exit(1)
    return value

AWS_CONFIG = {
    "aws_access_key_id": get_required_env("AWS_ACCESS_KEY_ID", "para acceso a AWS"),
    "aws_secret_access_key": get_required_env("AWS_SECRET_ACCESS_KEY", "para acceso a AWS"),
    "bucket_name": get_required_env("S3_BUCKET_NAME", "para el bucket S3"),
    "region_name": os.getenv("AWS_REGION", "us-east-2")  # Región por defecto válida
}

# Configuración específica AES  
ENCRYPTION_PASSWORD = get_required_env('ENCRYPTION_PASSWORD', 'para encriptación AES')

# Configuración específica KMS
KMS_KEY_ID = get_required_env('KMS_KEY_ID', 'para encriptación KMS')