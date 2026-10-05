import logging
import os
from contextlib import asynccontextmanager
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Job, JobCreate, JobOut, JobUpdate, Stats, Status

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("jobtrack")

APP_VERSION = os.getenv("APP_VERSION", "dev")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    log.info("JobTrack API %s started", APP_VERSION)
    yield


app = FastAPI(title="JobTrack API", version=APP_VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Business metrics (scraped by Prometheus at /metrics)
JOBS_CREATED = Counter("jobtrack_jobs_created_total", "Job applications added", ["source"])
STATUS_CHANGES = Counter("jobtrack_status_changes_total", "Status changes", ["status"])
JOBS_BY_STATUS = Gauge("jobtrack_jobs_by_status", "Current jobs per status", ["status"])

Instrumentator().instrument(app).expose(app, include_in_schema=False)


def refresh_gauges(db: Session) -> None:
    counts = dict(db.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    for s in Status:
        JOBS_BY_STATUS.labels(status=s.value).set(counts.get(s.value, 0))


@app.get("/healthz", include_in_schema=False)
def healthz():
    """Liveness: the process is up."""
    return {"status": "ok", "version": APP_VERSION}


@app.get("/readyz", include_in_schema=False)
def readyz(db: Session = Depends(get_db)):
    """Readiness: the database is reachable."""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        log.error("DB not ready: %s", exc)
        raise HTTPException(status_code=503, detail="database unavailable")
    return {"status": "ready"}


@app.get("/api/jobs", response_model=list[JobOut])
def list_jobs(status_filter: Status | None = None, db: Session = Depends(get_db)):
    q = select(Job).order_by(Job.applied_on.desc(), Job.id.desc())
    if status_filter:
        q = q.where(Job.status == status_filter.value)
    return db.scalars(q).all()


@app.post("/api/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    job = Job(
        company=payload.company.strip(),
        title=payload.title.strip(),
        source=payload.source.strip() or "LinkedIn",
        status=payload.status.value,
        applied_on=payload.applied_on or date.today(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    JOBS_CREATED.labels(source=job.source).inc()
    refresh_gauges(db)
    return job


@app.patch("/api/jobs/{job_id}", response_model=JobOut)
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    job.status = payload.status.value
    db.commit()
    db.refresh(job)
    STATUS_CHANGES.labels(status=job.status).inc()
    refresh_gauges(db)
    return job


@app.delete("/api/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    db.delete(job)
    db.commit()
    refresh_gauges(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/stats", response_model=Stats)
def stats(db: Session = Depends(get_db)):
    refresh_gauges(db)
    by_status = dict(db.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    by_source = dict(db.execute(select(Job.source, func.count()).group_by(Job.source)).all())
    total = sum(by_status.values())
    responded = total - by_status.get(Status.applied.value, 0)
    interviews = by_status.get(Status.interview.value, 0) + by_status.get(Status.offer.value, 0)
    return Stats(
        total=total,
        by_status={s.value: by_status.get(s.value, 0) for s in Status},
        by_source=by_source,
        response_rate=round(responded / total * 100, 1) if total else 0.0,
        interview_rate=round(interviews / total * 100, 1) if total else 0.0,
    )
