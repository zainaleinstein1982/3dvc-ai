from minio import Minio
from minio.error import S3Error
import io
import os
import logging
import re
from datetime import timedelta
from typing import Optional

log = logging.getLogger(__name__)

class ObjectStorage:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket = os.getenv("MINIO_BUCKET", "3dvc-ai-assets")
        self.client = None
        self.is_available = False
        try:
            self.client = Minio(self.endpoint, access_key=self.access_key, secret_key=self.secret_key, secure=False)
            if not self.client.bucket_exists(self.bucket): self.client.make_bucket(self.bucket)
            self.is_available = True
        except Exception as e:
            log.warning("MinIO unavailable: %s", e)

    def sanitize_key_component(self, component: str) -> str:
        component = re.sub(r'[\\/*?:"<>|]', "", component)
        if component in [".", ".."]: raise ValueError("Invalid path component")
        return component

    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> bool:
        if not self.is_available: return False
        try:
            self.client.put_object(self.bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)
            return True
        except Exception: return False

    def get_signed_url(self, key: str, expiry: int = 60) -> Optional[str]:
        if not self.is_available: return None
        try: return self.client.presigned_get_object(self.bucket, key, expires=timedelta(seconds=expiry))
        except Exception: return None

object_storage = ObjectStorage()
