from ..groq_client import groq_client
from ..schemas import (
    ResearchPlan, Claim, Verdict, SearchResult, ReportSection, Reference,
    FinalReport, ReportStats, Audience,
)

SYSTEM = """You are the Report Writer agent in a research pipeline. You are \
given a research plan, and for each sub-question a set of vetted claims \
(each already labeled with a verdict and confidence). Write the final report.

Rules:
- Write one section per sub-question, in the given order.
- Each section body should be 2-4 sentences of flowing prose synthesizing the \
claims for that sub-question - do not just list the claims.
- Weave claim_ids into the body inline exactly like this: [[claim_id]] right \
after the sentence that uses that claim, so the reader can see which \
statement each citation supports. Every claim_id you were given for a \
sub-question must appear at least once across the report.
- Do not state a claim more confidently than its verdict warrants - hedge \
"plausible" and "unverified" claims with words like "reportedly" or "one source suggests".
- Write a short executive summary (3-4 sentences) covering the overall answer.
- Tone: match the requested audience.
- Respond with ONLY a JSON object:
{
  "title": "...",
  "executive_summary": "...",
  "sections": [{"heading": "...", "sub_question_id": "...", "body": "... [[claim_id]] ..."}]
}
"""


def _format_input(plan: ResearchPlan, claims: list[Claim], verdicts_by_claim: dict[str, Verdict], audience: Audience) -> str:
    blocks = [f"Main query: {plan.main_query}\nGoal: {plan.restated_goal}\nAudience: {audience.value}\n"]
    for sq in plan.sub_questions:
        blocks.append(f"\n## Sub-question {sq.id}: {sq.text}")
        sq_claims = [c for c in claims if c.sub_question_id == sq.id]
        if not sq_claims:
            blocks.append("(No vetted claims were found for this sub-question.)")
            continue
        for c in sq_claims:
            v = verdicts_by_claim.get(c.claim_id)
            v_desc = f"{v.verdict.value}/{v.confidence.value}" if v else "unverified"
            blocks.append(f"- [{c.claim_id}] ({v_desc}) {c.text}")
    return "\n".join(blocks)


async def run_report_writer(
    plan: ResearchPlan,
    claims: list[Claim],
    verdicts: list[Verdict],
    sources_by_id: dict[str, SearchResult],
    audience: Audience,
    elapsed_seconds: float,
) -> FinalReport:
    verdicts_by_claim = {v.claim_id: v for v in verdicts}
    user = _format_input(plan, claims, verdicts_by_claim, audience)

    try:
        data = await groq_client.complete_json(SYSTEM, user, temperature=0.5, reasoning_effort="medium")
    except Exception:
        data = {}

    sections = []
    for s in data.get("sections", []):
        sq_id = s.get("sub_question_id", "")
        claim_ids = [c.claim_id for c in claims if c.sub_question_id == sq_id]
        sections.append(
            ReportSection(
                heading=s.get("heading", "Findings"),
                sub_question_id=sq_id,
                body=s.get("body", ""),
                claim_ids=claim_ids,
            )
        )

    if not sections:
        # Defensive fallback: build a minimal report directly from claims so the
        # user always gets something even if the writer model call failed.
        for sq in plan.sub_questions:
            sq_claims = [c for c in claims if c.sub_question_id == sq.id]
            body = " ".join(f"{c.text} [[{c.claim_id}]]" for c in sq_claims) or "No findings."
            sections.append(ReportSection(heading=sq.text, sub_question_id=sq.id, body=body,
                                           claim_ids=[c.claim_id for c in sq_claims]))

    seen_sources: dict[str, Reference] = {}
    for c in claims:
        for sid in c.source_ids:
            src = sources_by_id.get(sid)
            if src and sid not in seen_sources:
                seen_sources[sid] = Reference(
                    source_id=sid, url=src.url, title=src.title,
                    domain=src.domain, source_type=src.source_type,
                )

    n_verified = sum(1 for v in verdicts if v.verdict.value == "verified")
    n_contradicted = sum(1 for v in verdicts if v.verdict.value == "contradicted")

    return FinalReport(
        title=data.get("title", plan.main_query),
        executive_summary=data.get("executive_summary", plan.restated_goal),
        sections=sections,
        claims=claims,
        verdicts=verdicts,
        references=list(seen_sources.values()),
        stats=ReportStats(
            sub_questions=len(plan.sub_questions),
            sources_consulted=len(seen_sources),
            claims_extracted=len(claims),
            claims_verified=n_verified,
            claims_contradicted=n_contradicted,
            elapsed_seconds=round(elapsed_seconds, 1),
        ),
    )
