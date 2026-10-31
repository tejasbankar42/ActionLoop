import csv
import io
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import approval_out, audit_out, document_out, workflow_summary
from app.core.security import get_current_user
from app.database.session import get_db
from app.models import Approval, AuditEvent, Document, User, Workflow
from app.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    out = analytics_service.overview(db, user.organization_id)
    out["recent_documents"] = [document_out(d) for d in db.execute(
        select(Document).where(Document.organization_id == user.organization_id, Document.is_seeded.is_(False))
        .order_by(Document.created_at.desc()).limit(6)).scalars()]
    out["recent_workflows"] = [workflow_summary(w) for w in db.execute(
        select(Workflow).join(Document).where(Document.organization_id == user.organization_id)
        .order_by(Workflow.created_at.desc()).limit(8)).scalars()]
    out["pending_preview"] = [approval_out(a) | {"filename": db.get(Workflow, a.workflow_id).document.filename,
                                                 "document_type": db.get(Workflow, a.workflow_id).document_type}
                              for a in db.execute(select(Approval).where(Approval.status == "pending")
                                                  .order_by(Approval.created_at.desc()).limit(4)).scalars()]
    out["recent_audit"] = [audit_out(e) for e in db.execute(
        select(AuditEvent).order_by(AuditEvent.sequence.desc()).limit(8)).scalars()]
    return out


def _range(start: date | None, end: date | None) -> tuple[date, date]:
    end = end or date.today()
    start = start or end - timedelta(days=29)
    if start > end:
        raise HTTPException(422, "'from' must be on or before 'to'")
    if (end - start).days > 366:
        raise HTTPException(422, "Range is limited to one year")
    return start, end


@router.get("/reports")
def reports(start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s, e = _range(start, end)
    return analytics_service.report(db, user.organization_id, s, e)


@router.get("/reports.csv")
def reports_csv(start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    s, e = _range(start, end)
    r = analytics_service.report(db, user.organization_id, s, e)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "documents", "completed", "avg_end_to_end_s", "avg_automated_s"])
    for d in r["daily"]:
        w.writerow([d["date"], d["documents"], d["completed"], d["avg_end_to_end_s"] or "", d["avg_automated_s"] or ""])
    w.writerow([])
    w.writerow(["metric", "value"])
    for k, v in r["rates"].items():
        w.writerow([k, v if v is not None else ""])
    w.writerow(["seeded_workflows_in_range (illustrative)", r["seeded_workflows"]])
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="actionloop-report-{s}-{e}.csv"'})
