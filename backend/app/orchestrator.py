import time
import asyncio

from .schemas import ResearchRequest, StageStatus, SearchResult
from .job_store import job_store
from .config import settings
from .agents.planner import run_planner
from .agents.search_agent import run_search_agent
from .agents.summarizer import run_summarizer
from .agents.fact_checker import run_fact_checker
from .agents.report_writer import run_report_writer


async def _research_sub_question(sq, sources_per_question: int):
    """Search + summarize for one sub-question. Run in parallel across all
    sub-questions - this is the pipeline's main concurrency win.
    """
    results = await run_search_agent(sq, sources_per_question)
    claims = await run_summarizer(sq, results)
    return sq.id, results, claims


async def run_pipeline(job_id: str, request: ResearchRequest):
    start = time.monotonic()
    preset = settings.depth_presets[request.depth.value]

    try:
        # ---- Stage 1: Planner --------------------------------------------
        job_store.set_stage(job_id, "planner", StageStatus.running)
        plan = await run_planner(request.query, request.depth, request.audience)
        job_store.get(job_id).plan = plan
        job_store.set_stage(
            job_id, "planner", StageStatus.done,
            f"{len(plan.sub_questions)} sub-questions identified",
        )

        # ---- Stage 2 + 3: Search & Summarize (parallel per sub-question) --
        job_store.set_stage(job_id, "search", StageStatus.running)
        job_store.set_stage(job_id, "summarizer", StageStatus.running)

        outcomes = await asyncio.gather(
            *[_research_sub_question(sq, preset["sources_per_question"]) for sq in plan.sub_questions]
        )

        all_results: list[SearchResult] = []
        all_claims = []
        for _, results, claims in outcomes:
            all_results.extend(results)
            all_claims.extend(claims)
        sources_by_id = {r.source_id: r for r in all_results}

        job_store.set_stage(job_id, "search", StageStatus.done, f"{len(all_results)} sources retrieved")
        job_store.set_stage(job_id, "summarizer", StageStatus.done, f"{len(all_claims)} claims extracted")

        # ---- Stage 4: Fact-checker ----------------------------------------
        job_store.set_stage(job_id, "fact_checker", StageStatus.running)
        verdicts = await run_fact_checker(all_claims, sources_by_id)
        n_verified = sum(1 for v in verdicts if v.verdict.value == "verified")
        job_store.set_stage(
            job_id, "fact_checker", StageStatus.done,
            f"{n_verified}/{len(verdicts)} claims verified",
        )

        # ---- Stage 5: Report writer ----------------------------------------
        job_store.set_stage(job_id, "writer", StageStatus.running)
        elapsed = time.monotonic() - start
        report = await run_report_writer(
            plan, all_claims, verdicts, sources_by_id, request.audience, elapsed,
        )
        job_store.set_stage(job_id, "writer", StageStatus.done, "Report ready")

        job_store.complete(job_id, plan, report)

    except Exception as e:
        current = next((s.key for s in job_store.get(job_id).stages if s.status == StageStatus.running), "planner")
        job_store.fail(job_id, current, str(e))
