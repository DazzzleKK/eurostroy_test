"""Хранилище изображений в MinIO/S3.

Официальный клиент ``minio`` синхронный, поэтому вызовы уходят в пул потоков:
event loop FastAPI не должен ждать сеть до S3.
"""

from __future__ import annotations

import asyncio
import io

from minio import Minio
from minio.error import S3Error

from eurostroy.config import Settings

_MISSING_CODES = frozenset({"NoSuchKey", "NoSuchObject", "NoSuchBucket"})


class MinioImageStorage:
    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @classmethod
    def from_settings(cls, settings: Settings) -> MinioImageStorage:
        client = Minio(
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
            region=settings.s3_region,
        )
        return cls(client, settings.s3_bucket)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._put, key, data, content_type)

    async def get(self, key: str) -> bytes | None:
        return await asyncio.to_thread(self._get, key)

    async def ensure_bucket(self) -> None:
        await asyncio.to_thread(self._ensure_bucket)

    async def ping(self) -> bool:
        return await asyncio.to_thread(self._ping)

    async def ping_server(self) -> bool:
        """Проверка «сервер отвечает», без требования существующего бакета."""
        return await asyncio.to_thread(self._ping_server)

    def _put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def _get(self, key: str) -> bytes | None:
        try:
            response = self._client.get_object(self._bucket, key)
        except S3Error as exc:
            if exc.code in _MISSING_CODES:
                return None
            raise
        try:
            return bytes(response.read())
        finally:
            response.close()
            response.release_conn()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def _ping(self) -> bool:
        try:
            return bool(self._client.bucket_exists(self._bucket))
        except S3Error:
            return False

    def _ping_server(self) -> bool:
        try:
            self._client.list_buckets()
        except Exception:
            return False
        return True
