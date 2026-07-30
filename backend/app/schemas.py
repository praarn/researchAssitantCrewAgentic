from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request / job envelope
# ---------------------------------------------------------------------------

class Depth(str, Enum):
    quick = "quick"
    standard = "standard"
    deep = "deep"


class Audience(str, Enum):
    general = "general"
    technical = "technical"
    executive = "executive"


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    depth: Depth = Depth.standard
    audience: Audience = Audience.general


class StageStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class Stage(BaseModel):
    key: str
    label: str
    status: StageStatus = StageStatus.pending
    detail: str = ""


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class SubQuestion(BaseModel):
    id: str
    text: str
    rationale: str = ""


class ResearchPlan(BaseModel):
    main_query: str
    restated_goal: str
    sub_questions: List[SubQuestion]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    news = "news"
    reference = "reference"
    academic = "academic"
    official = "official"
    blog_or_forum = "blog_or_forum"
    other = "other"


class SearchResult(BaseModel):
    source_id: str
    sub_question_id: str
    url: str
    title: str
    domain: str
    source_type: SourceType = SourceType.other
    published: Optional[str] = None
    snippet: str = ""
    content: str = ""
    quality_score: float = 0.5


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

class Agreement(str, Enum):
    corroborated = "corroborated"
    single_source = "single_source"
    contradicted = "contradicted"


class Claim(BaseModel):
    claim_id: str
    sub_question_id: str
    text: str
    source_ids: List[str]
    agreement: Agreement = Agreement.single_source


# ---------------------------------------------------------------------------
# Fact checker
# ---------------------------------------------------------------------------

class VerdictLabel(str, Enum):
    verified = "verified"
    plausible = "plausible"
    unverified = "unverified"
    contradicted = "contradicted"


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Verdict(BaseModel):
    claim_id: str
    verdict: VerdictLabel
    confidence: Confidence
    method: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

class ReportSection(BaseModel):
    heading: str
    sub_question_id: str
    body: str
    claim_ids: List[str] = []


class Reference(BaseModel):
    source_id: str
    url: str
    title: str
    domain: str
    source_type: SourceType = SourceType.other


class ReportStats(BaseModel):
    sub_questions: int
    sources_consulted: int
    claims_extracted: int
    claims_verified: int
    claims_contradicted: int
    elapsed_seconds: float


class FinalReport(BaseModel):
    title: str
    executive_summary: str
    sections: List[ReportSection]
    claims: List[Claim]
    verdicts: List[Verdict]
    references: List[Reference]
    stats: ReportStats


# ---------------------------------------------------------------------------
# Job (full pipeline state, returned to the frontend)
# ---------------------------------------------------------------------------

class Job(BaseModel):
    id: str
    status: JobStatus = JobStatus.queued
    request: ResearchRequest
    stages: List[Stage]
    plan: Optional[ResearchPlan] = None
    report: Optional[FinalReport] = None
    error: Optional[str] = None
