import os

# Configuración común AWS
AWS_CONFIG = {
    'region_name': os.getenv('AWS_REGION', 'us-east-1'),
    'aws_access_key_id': os.getenv('AWS_ACCESS_KEY_ID'),
    'aws_secret_access_key': os.getenv('AWS_SECRET_ACCESS_KEY'),
    'bucket_name': os.getenv('S3_BUCKET_NAME', 'default-bucket')
}

# Configuración específica AES
ENCRYPTION_PASSWORD = os.getenv('ENCRYPTION_PASSWORD', 'default-password')

# Configuración específica KMS
KMS_KEY_ID = os.getenv('KMS_KEY_ID', 'default-kms-key')