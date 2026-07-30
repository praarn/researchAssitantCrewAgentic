from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ResearchRequest, Job
from .job_store import job_store
from .orchestrator import run_pipeline
from .config import settings

app = FastAPI(title="Research Assistant Crew", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "groq_key_configured": bool(settings.groq_api_key)}


@app.post("/api/research", response_model=Job)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    job = job_store.create(request)
    background_tasks.add_task(run_pipeline, job.id, request)
    return job


@app.get("/api/research/{job_id}", response_model=Job)
async def get_research(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
