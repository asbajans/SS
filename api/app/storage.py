"""MinIO object storage helpers (async)."""
from io import BytesIO

from miniopy_async import Minio

from app.config import settings

_bucket_ready = False


def _client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )


async def ensure_bucket() -> None:
    global _bucket_ready
    if _bucket_ready:
        return
    client = _client()
    try:
        if not await client.bucket_exists(settings.minio_bucket):
            await client.make_bucket(settings.minio_bucket)
        _bucket_ready = True
    finally:
        await client.close_session()


async def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    await ensure_bucket()
    client = _client()
    try:
        await client.put_object(
            settings.minio_bucket, key, BytesIO(data), len(data), content_type=content_type
        )
    finally:
        await client.close_session()


async def get_bytes(key: str) -> bytes:
    client = _client()
    try:
        resp = await client.get_object(settings.minio_bucket, key)
        try:
            return await resp.read()
        finally:
            resp.close()
    finally:
        await client.close_session()


async def delete_object(key: str) -> None:
    client = _client()
    try:
        await client.remove_object(settings.minio_bucket, key)
    finally:
        await client.close_session()
