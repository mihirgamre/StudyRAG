from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Protocol


class ObjectStorage(Protocol):
    def put_file(self, path: str | Path, *, object_key: str, content_type: str | None = None) -> str:
        ...


class LocalObjectStorage:
    """Filesystem-backed storage for development and tests.

    Production Cloudflare R2/S3 uses `S3CompatibleObjectStorage`; this local
    implementation keeps the same write contract without requiring external
    credentials during local ingestion tests.
    """

    def __init__(self, root_dir: str | Path, *, url_prefix: str = "local://") -> None:
        self.root_dir = Path(root_dir)
        self.url_prefix = url_prefix if url_prefix.endswith("://") else url_prefix.rstrip("/") + "/"

    def put_file(self, path: str | Path, *, object_key: str, content_type: str | None = None) -> str:
        destination = self.root_dir / object_key
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        return f"{self.url_prefix}{object_key.replace(os.sep, '/')}"


class S3CompatibleObjectStorage:
    """Cloudflare R2/S3-compatible original file storage."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        public_base_url: str | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("bucket is required")

        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "S3/R2 storage requires boto3. Install with: pip install -e '.[ingestion]'"
            ) from exc

        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def put_file(self, path: str | Path, *, object_key: str, content_type: str | None = None) -> str:
        extra_args = {"ContentType": content_type} if content_type else None
        kwargs = {"ExtraArgs": extra_args} if extra_args else {}
        self._client.upload_file(str(path), self.bucket, object_key, **kwargs)
        if self.public_base_url:
            return f"{self.public_base_url}/{object_key}"
        return f"s3://{self.bucket}/{object_key}"


def object_key_for_document(document_id: uuid.UUID | str, filename: str) -> str:
    safe_name = _safe_filename(filename)
    return f"documents/{document_id}/{safe_name}"


def source_type_from_filename(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    if suffix == ".txt":
        return "txt"
    if suffix in {".ppt", ".pptx"}:
        return "slides"
    raise ValueError(f"unsupported document type: {suffix or '<none>'}")


def storage_from_env() -> ObjectStorage:
    backend = os.getenv("STUDYRAG_STORAGE_BACKEND", "local").lower()
    if backend == "local":
        return LocalObjectStorage(os.getenv("STUDYRAG_LOCAL_STORAGE_DIR", ".studyrag_storage"))
    if backend in {"s3", "r2"}:
        return S3CompatibleObjectStorage(
            bucket=os.getenv("S3_BUCKET", ""),
            region=os.getenv("S3_REGION"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
            public_base_url=os.getenv("S3_PUBLIC_BASE_URL"),
        )
    raise ValueError(f"unsupported STUDYRAG_STORAGE_BACKEND: {backend}")


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return sanitized or "upload"
