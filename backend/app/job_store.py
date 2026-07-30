import uuid
from typing import Dict, Optional

from .schemas import Job, JobStatus, ResearchRequest, Stage, StageStatus

PIPELINE_STAGES = [
    ("planner", "Planning research"),
    ("search", "Searching the web"),
    ("summarizer", "Extracting claims"),
    ("fact_checker", "Cross-checking facts"),
    ("writer", "Writing report"),
]


class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    def create(self, request: ResearchRequest) -> Job:
        job_id = uuid.uuid4().hex[:12]
        stages = [Stage(key=k, label=label) for k, label in PIPELINE_STAGES]
        job = Job(id=job_id, request=request, stages=stages)
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def set_stage(self, job_id: str, key: str, status: StageStatus, detail: str = ""):
        job = self._jobs[job_id]
        for stage in job.stages:
            if stage.key == key:
                stage.status = status
                if detail:
                    stage.detail = detail
        if status == StageStatus.running:
            job.status = JobStatus.running

    def fail(self, job_id: str, key: str, message: str):
        job = self._jobs[job_id]
        job.status = JobStatus.failed
        job.error = message
        for stage in job.stages:
            if stage.key == key:
                stage.status = StageStatus.error
                stage.detail = message

    def complete(self, job_id: str, plan, report):
        job = self._jobs[job_id]
        job.plan = plan
        job.report = report
        job.status = JobStatus.complete


job_store = JobStore()
