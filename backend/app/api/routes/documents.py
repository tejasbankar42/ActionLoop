import hashlib

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import document_out
from app.core.config import get_settings
from app.core.security import get_current_user, require_role
from app.database.session import get_db
from app.models import Document, User
from app.services import audit_service
from app.services.storage import get_storage

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg"}
MAGIC = {".pdf": [b"%PDF"], ".png": [b"\x89PNG"], ".jpg": [b"\xff\xd8\xff"]}


@router.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(require_role("operator"))):
    s = get_settings()
    ext = ALLOWED.get(file.content_type or "")
    name = (file.filename or "document").rsplit("/", 1)[-1].rsplit("\\", 1)[-1][:200]
    if not ext or not name.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF, JPG, JPEG and PNG files are accepted")
    data = await file.read(s.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {s.max_upload_mb} MB")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is empty")
    if not any(data.startswith(m) for m in MAGIC[ext]):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File content does not match its declared type")
    digest = hashlib.sha256(data).hexdigest()
    previous = db.execute(select(Document).where(Document.sha256 == digest, Document.organization_id == user.organization_id,
                                                 Document.is_sample.is_(False))).scalars().first()
    key = get_storage().save(data, ext)
    doc = Document(organization_id=user.organization_id, uploaded_by=user.id, filename=name, content_type=file.content_type,
                   size_bytes=len(data), sha256=digest, storage_key=key)
    db.add(doc)
    db.commit()
    audit_service.append_event(db, event_type="DOCUMENT_UPLOADED", description=f"Uploaded '{name}' ({len(data):,} bytes).",
                               actor=user.full_name, user_id=user.id, payload={"document_id": doc.id, "sha256": digest})
    out = document_out(doc)
    out["duplicate_upload_of"] = previous.id if previous else None
    return out


@router.get("")
def list_documents(
    include_seeded: bool = Query(False), limit: int = Query(50, le=200),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    q = select(Document).where(Document.organization_id == user.organization_id)
    if not include_seeded:
        q = q.where(Document.is_seeded.is_(False))
    docs = db.execute(q.order_by(Document.created_at.desc()).limit(limit)).scalars().all()
    return [document_out(d) for d in docs]


def _get(db: Session, doc_id: str, user: User) -> Document:
    doc = db.get(Document, doc_id)
    if not doc or doc.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return doc


@router.get("/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return document_out(_get(db, doc_id, user), with_workflows=True)


@router.get("/{doc_id}/file")
def get_file(doc_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    doc = _get(db, doc_id, user)
    if doc.storage_key == "seeded-no-file":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Seeded history has no stored file")
    return FileResponse(get_storage().path(doc.storage_key), media_type=doc.content_type,
                        headers={"Content-Disposition": f'inline; filename="{doc.filename}"',
                                 "X-Content-Type-Options": "nosniff"})
