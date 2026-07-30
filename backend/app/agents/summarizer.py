from ..groq_client import groq_client
from ..schemas import SubQuestion, SearchResult, Claim, Agreement

SYSTEM = """You are the Summarizer agent in a research pipeline. Given a \
sub-question and excerpts from several web sources, extract the distinct \
factual claims relevant to answering the sub-question.

Rules:
- Each claim must be a single, specific, checkable statement (not an opinion).
- Attach the source_ids that support each claim (use the exact ids given).
- If two or more sources support the same claim, mark agreement as "corroborated".
- If only one source supports a claim, mark it "single_source".
- If sources directly disagree, create separate claims for each side and mark both "contradicted".
- Skip filler / marketing language, keep only substantive facts.
- Produce at most 6 claims total.
- Respond with ONLY a JSON object:
{"claims": [{"text": "...", "source_ids": ["..."], "agreement": "corroborated|single_source|contradicted"}]}
"""


def _format_sources(results: list[SearchResult]) -> str:
    blocks = []
    for r in results:
        excerpt = (r.content or r.snippet or "")[:1500]
        if not excerpt:
            continue
        blocks.append(f"[source_id={r.source_id}] ({r.domain})\n{excerpt}")
    return "\n\n".join(blocks) if blocks else "No usable content was retrieved for this sub-question."


async def run_summarizer(sub_question: SubQuestion, results: list[SearchResult]) -> list[Claim]:
    user = (
        f"Sub-question: {sub_question.text}\n\n"
        f"Sources:\n{_format_sources(results)}"
    )
    try:
        data = await groq_client.complete_json(SYSTEM, user)
    except Exception:
        return []

    valid_ids = {r.source_id for r in results}
    claims = []
    for i, c in enumerate(data.get("claims", [])):
        text = (c.get("text") or "").strip()
        if not text:
            continue
        source_ids = [sid for sid in c.get("source_ids", []) if sid in valid_ids]
        if not source_ids:
            continue
        agreement_raw = c.get("agreement", "single_source")
        agreement = agreement_raw if agreement_raw in Agreement._value2member_map_ else "single_source"
        claims.append(
            Claim(
                claim_id=f"{sub_question.id}-c{i+1}",
                sub_question_id=sub_question.id,
                text=text,
                source_ids=source_ids,
                agreement=Agreement(agreement),
            )
        )
    return claims
