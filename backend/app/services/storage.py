"""File storage behind a small interface so production can swap in object storage."""

import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


class StorageAdapter(ABC):
    @abstractmethod
    def save(self, data: bytes, suffix: str) -> str: ...

    @abstractmethod
    def read(self, key: str) -> bytes: ...

    @abstractmethod
    def path(self, key: str) -> Path: ...


class LocalStorage(StorageAdapter):
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, suffix: str) -> str:
        # Server-generated names only: user-supplied filenames never touch the filesystem.
        key = f"{uuid.uuid4().hex}{suffix}"
        (self.root / key).write_bytes(data)
        return key

    def path(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root not in p.parents:
            raise ValueError("Invalid storage key")
        return p

    def read(self, key: str) -> bytes:
        return self.path(key).read_bytes()


class ObjectStorage(StorageAdapter):  # pragma: no cover - documented extension point
    """Placeholder for S3/GCS/Azure Blob. Not implemented in this prototype."""

    def save(self, data: bytes, suffix: str) -> str:
        raise NotImplementedError

    def read(self, key: str) -> bytes:
        raise NotImplementedError

    def path(self, key: str) -> Path:
        raise NotImplementedError


@lru_cache
def get_storage() -> StorageAdapter:
    return LocalStorage(get_settings().storage_dir)
