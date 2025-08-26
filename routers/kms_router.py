from fastapi import APIRouter, Depends, File, UploadFile, Form, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging
from config import AWS_CONFIG, KMS_KEY_ID
from utils.s3_kms_uploader import S3KMSUploader

kms_router = APIRouter(tags=["KMS Encryption"])
logger = logging.getLogger(__name__)

class UploadResponse(BaseModel):
    success: bool
    message: str
    s3_key: Optional[str] = None
    file_size: Optional[int] = None

class MultipleUploadResponse(BaseModel):
    results: List[UploadResponse]
    total_files: int
    successful_uploads: int

class S3Object(BaseModel):
    key: str
    size: int
    last_modified: datetime
    etag: str

class S3ObjectList(BaseModel):
    objects: List[S3Object]
    total_count: int
    prefix: Optional[str] = None

def get_kms_uploader():
    try:
        # Validar que todas las configuraciones requeridas están presentes
        required_configs = {
            'bucket_name': AWS_CONFIG.get('bucket_name'),
            'aws_access_key_id': AWS_CONFIG.get('aws_access_key_id'),
            'aws_secret_access_key': AWS_CONFIG.get('aws_secret_access_key'),
            'region_name': AWS_CONFIG.get('region_name')
        }
        
        # Verificar que ninguna configuración crítica sea None o vacía
        missing_configs = []
        for key, value in required_configs.items():
            if not value or not isinstance(value, str):
                missing_configs.append(key)
        
        if missing_configs:
            error_msg = f"Missing or invalid AWS configuration: {', '.join(missing_configs)}"
            logger.error(error_msg)
            raise HTTPException(500, error_msg)
        
        # Validar KMS_KEY_ID
        if not KMS_KEY_ID or not isinstance(KMS_KEY_ID, str):
            error_msg = "KMS_KEY_ID is missing or invalid"
            logger.error(error_msg)
            raise HTTPException(500, error_msg)
        
        # Log para debugging
        logger.info(f"Initializing S3KMSUploader with:")
        logger.info(f"  bucket_name: {required_configs['bucket_name']}")
        logger.info(f"  region_name: {required_configs['region_name']}")
        logger.info(f"  kms_key_id: {KMS_KEY_ID}")
        
        uploader = S3KMSUploader(
            bucket_name=required_configs['bucket_name'],
            kms_key_id=KMS_KEY_ID,
            aws_access_key_id=required_configs['aws_access_key_id'],
            aws_secret_access_key=required_configs['aws_secret_access_key'],
            region_name=required_configs['region_name']
        )
        
        if not uploader.verify_bucket_access():
            raise Exception("Bucket access verification failed")
        
        return uploader
        
    except HTTPException:
        # Re-lanzar HTTPException tal como está
        raise
    except Exception as e:
        logger.error(f"Uploader init failed: {e}")
        raise HTTPException(500, f"S3 uploader initialization failed: {str(e)}")

@kms_router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    s3_key: Optional[str] = Form(None),
    metadata_key: Optional[str] = Form(None),
    metadata_value: Optional[str] = Form(None),
    uploader: S3KMSUploader = Depends(get_kms_uploader)
):
    try:
        content = await file.read()
        if not s3_key:
            unique_id = str(uuid.uuid4())[:8]
            s3_key = f"{unique_id}_{file.filename}"
        
        content_type = uploader._get_content_type(file.filename)
        metadata = {'original_filename': file.filename}
        
        if metadata_key and metadata_value:
            metadata[metadata_key] = metadata_value
        
        success = uploader.upload_file_from_memory(
            content,
            s3_key,
            content_type,
            metadata
        )
        
        if success:
            return UploadResponse(
                success=True,
                message="File uploaded successfully",
                s3_key=s3_key,
                file_size=len(content)
            )
        raise HTTPException(500, "Upload failed")
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@kms_router.get("/objects", response_model=S3ObjectList)
async def list_objects(
    prefix: str = Query(""),
    uploader: S3KMSUploader = Depends(get_kms_uploader)
):
    try:
        objects = uploader.list_objects(prefix)
        return S3ObjectList(
            objects=[S3Object(
                key=obj['Key'],
                size=obj['Size'],
                last_modified=obj['LastModified'],
                etag=obj['ETag']
            ) for obj in objects],
            total_count=len(objects),
            prefix=prefix or None
        )
    except Exception as e:
        logger.error(f"List error: {e}")
        raise HTTPException(500, f"List failed: {str(e)}")

# Endpoint para verificar la configuración (útil para debugging)
@kms_router.get("/health")
async def health_check():
    try:
        # Intentar crear el uploader para verificar la configuración
        uploader = get_kms_uploader()
        return {
            "status": "healthy",
            "message": "KMS uploader configuration is valid",
            "region": AWS_CONFIG.get('region_name'),
            "bucket": AWS_CONFIG.get('bucket_name')
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Configuration error: {str(e)}"
        }