from fastapi import APIRouter, File, UploadFile, HTTPException, Path
from fastapi.responses import StreamingResponse
import tempfile
import os
import logging
from datetime import datetime
import traceback
import boto3
from config import AWS_CONFIG, ENCRYPTION_PASSWORD
from utils.aes_encryptor import AES256FileEncryptor
from pydantic import BaseModel
from typing import Dict, Any, List

router = APIRouter(tags=["AES-256 Encryption"])
logger = logging.getLogger(__name__)

s3_client = None
encryptor = AES256FileEncryptor()

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Dict[Any, Any] = {}

class FileInfo(BaseModel):
    name: str
    encrypted_key: str
    size: str
    last_modified: str
    encryption: str
    original_size: str

def get_s3_client():
    global s3_client
    if not s3_client:
        try:
            s3_client = boto3.client(
                's3',
                region_name=AWS_CONFIG['region_name'],
                aws_access_key_id=AWS_CONFIG['aws_access_key_id'],
                aws_secret_access_key=AWS_CONFIG['aws_secret_access_key']
            )
        except Exception as e:
            logger.error(f"S3 init error: {e}")
            raise HTTPException(status_code=500, detail="S3 initialization failed")
    return s3_client

def format_file_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def secure_filename(filename):
    import re
    filename = re.sub(r'[^\w\s\.-]', '', filename).strip()
    return re.sub(r'[-\s]+', '-', filename)

@router.post("/upload-encrypted", response_model=APIResponse)
async def upload_encrypted(file: UploadFile = File(...)):
    s3_client = get_s3_client()
    filename = secure_filename(file.filename)
    
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_orig, \
             tempfile.NamedTemporaryFile(delete=False, suffix='.enc') as temp_enc:
            
            content = await file.read()
            temp_orig.write(content)
            temp_orig.close()
            
            encrypt_result = encryptor.encrypt_file(
                temp_orig.name,
                temp_enc.name,
                ENCRYPTION_PASSWORD
            )
            
            if not encrypt_result['success']:
                raise HTTPException(500, f"Encryption failed: {encrypt_result['error']}")
            
            encrypted_filename = f"{filename}.encrypted"
            
            with open(temp_enc.name, 'rb') as enc_file:
                s3_client.upload_fileobj(
                    enc_file,
                    AWS_CONFIG['bucket_name'],
                    encrypted_filename,
                    ExtraArgs={
                        'Metadata': {
                            'original-filename': filename,
                            'encrypted': 'true',
                            'encryption-algorithm': 'AES-256-CBC',
                            'original-size': str(encrypt_result['original_size']),
                            'original-hash': encrypt_result['original_hash']
                        }
                    }
                )
            
            return APIResponse(
                success=True,
                message=f"File encrypted and uploaded: {filename}",
                data={
                    'encrypted_filename': encrypted_filename,
                    'original_size': format_file_size(encrypt_result['original_size']),
                    'encrypted_size': format_file_size(encrypt_result['encrypted_size']),
                    'original_hash': encrypt_result['original_hash']
                }
            )
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")
    finally:
        for f in [temp_orig.name, temp_enc.name]:
            try:
                os.unlink(f)
            except:
                pass

@router.get("/download-decrypted/{filename}")
async def download_decrypted(filename: str):
    s3_client = get_s3_client()
    encrypted_filename = f"{filename}.encrypted"
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.enc') as temp_enc, \
             tempfile.NamedTemporaryFile(delete=False) as temp_dec:
            
            s3_client.download_file(
                AWS_CONFIG['bucket_name'],
                encrypted_filename,
                temp_enc.name
            )
            
            decrypt_result = encryptor.decrypt_file(
                temp_enc.name,
                temp_dec.name,
                ENCRYPTION_PASSWORD
            )
            
            if not decrypt_result['success']:
                raise HTTPException(500, f"Decryption failed: {decrypt_result['error']}")
            
            def file_generator():
                with open(temp_dec.name, 'rb') as f:
                    while chunk := f.read(8192):
                        yield chunk
                # Cleanup after streaming
                for f in [temp_enc.name, temp_dec.name]:
                    try:
                        os.unlink(f)
                    except:
                        pass
            
            return StreamingResponse(
                file_generator(),
                media_type='application/octet-stream',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(500, f"Download failed: {str(e)}")