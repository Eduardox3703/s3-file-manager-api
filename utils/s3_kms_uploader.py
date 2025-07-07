import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)

class S3KMSUploader:
    def __init__(self, 
                 bucket_name: str,
                 kms_key_id: str,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 region_name: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.kms_key_id = kms_key_id
        self.region_name = region_name
        
        try:
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
            self.s3_client = session.client('s3')
            logger.info(f"S3 client initialized for region: {region_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise

    def verify_bucket_access(self) -> bool:
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket access verified: {self.bucket_name}")
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Bucket access error: {error_code}")
            return False

    def upload_file_from_memory(self, 
                               file_content: bytes,
                               s3_key: str,
                               content_type: str = 'application/octet-stream',
                               metadata: Optional[Dict[str, str]] = None) -> bool:
        upload_args = {
            'ServerSideEncryption': 'aws:kms',
            'SSEKMSKeyId': self.kms_key_id,
            'ContentType': content_type
        }
        
        if metadata:
            upload_args['Metadata'] = metadata
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                **upload_args
            )
            return True
        except ClientError as e:
            logger.error(f"Upload error: {e}")
            return False

    def list_objects(self, prefix: str = '') -> List[Dict[str, Any]]:
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            return response.get('Contents', [])
        except ClientError as e:
            logger.error(f"List objects error: {e}")
            return []

    def delete_object(self, s3_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            logger.error(f"Delete error: {e}")
            return False

    def _get_content_type(self, filename: str) -> str:
        content_types = {
            '.txt': 'text/plain',
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.zip': 'application/zip',
            '.json': 'application/json',
            '.csv': 'text/csv',
            '.xml': 'application/xml',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        extension = Path(filename).suffix.lower()
        return content_types.get(extension, 'application/octet-stream')