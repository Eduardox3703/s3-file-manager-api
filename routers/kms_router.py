from fastapi import APIRouter, Depends, File, UploadFile, Form, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid
import logging
from config import AWS_CONFIG, KMS_KEY_ID
from utils.s3_kms_uploader import S3KMSUploader

router = APIRouter(tags=["KMS Encryption"])
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
        uploader = S3KMSUploader(
            bucket_name=AWS_CONFIG['bucket_name'],
            kms_key_id=KMS_KEY_ID,
            aws_access_key_id=AWS_CONFIG['aws_access_key_id'],
            aws_secret_access_key=AWS_CONFIG['aws_secret_access_key'],
            region_name=AWS_CONFIG['region_name']
        )
        if not uploader.verify_bucket_access():
            raise Exception("Bucket access verification failed")
        return uploader
    except Exception as e:
        logger.error(f"Uploader init failed: {e}")
        raise HTTPException(500, "S3 uploader initialization failed")

@router.post("/upload", response_model=UploadResponse)
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

@router.get("/objects", response_model=S3ObjectList)
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