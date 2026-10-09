from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import logging

from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, SessionLocal, get_db
from .models import GenerationJob, Recipient
from .schemas import JobCreate, JobResult
from .certificates import generate_certificate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Bulk Certificate Generator", version="1.0.0")

def run_generation(job_id: int):
    """Runs after the HTTP response; each recipient is isolated from others."""
    db = SessionLocal()
    try:
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if not job:
            return
        job.status = "processing"
        db.commit()
        recipient_ids = [r.id for r in job.recipients]
        for recipient_id in recipient_ids:
            recipient = db.query(Recipient).filter(Recipient.id == recipient_id).first()
            if recipient is None:
                continue
            recipient.status = "processing"
            db.commit()
            try:
                recipient.file_path = generate_certificate(
                    recipient.name, recipient.course, recipient.certificate_id
                )
                recipient.status = "succeeded"
                recipient.error = None
            except Exception as exc:
                logger.exception("Certificate generation failed for recipient %s", recipient.id)
                recipient.status = "failed"
                recipient.error = f"Generation failed: {type(exc).__name__}"
                recipient.file_path = None
            db.commit()
        db.refresh(job)
        job.succeeded = sum(1 for r in job.recipients if r.status == "succeeded")
        job.failed = sum(1 for r in job.recipients if r.status == "failed")
        job.status = "completed_with_errors" if job.failed else "completed"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        logger.exception("Job %s failed unexpectedly", job_id)
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()

def serialize_job(job: GenerationJob) -> dict:
    recipients = []
    for r in job.recipients:
        recipients.append({
            "id": r.id, "name": r.name, "email": r.email, "course": r.course,
            "certificate_id": r.certificate_id, "status": r.status, "error": r.error,
            "download_url": f"/certificates/{r.certificate_id}" if r.status == "succeeded" else None
        })
    progress = ((job.succeeded + job.failed) / job.total * 100) if job.total else 0.0
    return {
        "id": job.id, "status": job.status, "total": job.total,
        "succeeded": job.succeeded, "failed": job.failed,
        "progress_percent": round(progress, 2), "recipients": recipients
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/jobs", response_model=JobResult, status_code=202)
def create_job(payload: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = GenerationJob(status="queued", total=len(payload.recipients))
    db.add(job)
    db.flush()
    for item in payload.recipients:
        db.add(Recipient(
            job_id=job.id, name=item.name.strip(), email=str(item.email),
            course=item.course.strip(), certificate_id=f"CERT-{uuid4().hex[:12].upper()}",
            status="pending"
        ))
    db.commit()
    db.refresh(job)
    # Run in-process after returning response. For durable production queues use Celery/RQ.
    background_tasks.add_task(run_generation, job.id)
    return serialize_job(job)

@app.get("/jobs/{job_id}", response_model=JobResult)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(GenerationJob).options(selectinload(GenerationJob.recipients)).filter(
        GenerationJob.id == job_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return serialize_job(job)

@app.get("/certificates/{certificate_id}")
def get_certificate(certificate_id: str, db: Session = Depends(get_db)):
    recipient = db.query(Recipient).filter(Recipient.certificate_id == certificate_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if recipient.status != "succeeded" or not recipient.file_path:
        raise HTTPException(status_code=409, detail=f"Certificate is not available (status: {recipient.status})")
    path = Path(recipient.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Certificate file is missing")
    return FileResponse(path, media_type="application/pdf", filename=f"{certificate_id}.pdf")
