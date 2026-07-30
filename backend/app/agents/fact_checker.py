from ..groq_client import groq_client
from ..schemas import Claim, SearchResult, Verdict, VerdictLabel, Confidence, Agreement

SYSTEM = """You are the Fact-Checker agent in a research pipeline. You are \
given a batch of claims, each with the claim text and metadata about the \
source(s) behind it (source domain and a quality_score from 0-1 reflecting \
how reliable that domain generally is). Judge each claim on its own.

Rules:
- "corroborated" claims (2+ independent sources agree) should usually be "verified" \
unless the sources are all low quality, in which case "plausible".
- "single_source" claims should be "plausible" if the sole source is medium/high \
quality, or "unverified" if the source is low quality or the claim is vague.
- "contradicted" claims must be labeled "contradicted", and confidence should \
reflect how clear-cut the disagreement is.
- confidence is "high", "medium", or "low".
- Give a one-sentence note explaining the verdict.
- Respond with ONLY a JSON object:
{"verdicts": [{"claim_id": "...", "verdict": "verified|plausible|unverified|contradicted", "confidence": "high|medium|low", "notes": "..."}]}
"""


def _fast_path(claim: Claim, avg_quality: float) -> Verdict | None:
    """Cheap heuristic verdicts that don't need an LLM call, to save on
    rate-limited requests: strongly corroborated, high-quality claims.
    """
    if claim.agreement == Agreement.corroborated and avg_quality >= 0.85:
        return Verdict(
            claim_id=claim.claim_id,
            verdict=VerdictLabel.verified,
            confidence=Confidence.high,
            method="corroborated across multiple high-quality sources",
            notes="Multiple independent, high-quality sources agree on this claim.",
        )
    return None


async def run_fact_checker(claims: list[Claim], sources_by_id: dict[str, SearchResult]) -> list[Verdict]:
    verdicts: list[Verdict] = []
    needs_review: list[Claim] = []

    for claim in claims:
        qualities = [sources_by_id[sid].quality_score for sid in claim.source_ids if sid in sources_by_id]
        avg_quality = sum(qualities) / len(qualities) if qualities else 0.5
        fast = _fast_path(claim, avg_quality)
        if fast:
            verdicts.append(fast)
        else:
            needs_review.append(claim)

    if needs_review:
        lines = []
        for c in needs_review:
            src_desc = ", ".join(
                f"{sources_by_id[sid].domain} (quality={sources_by_id[sid].quality_score:.2f})"
                for sid in c.source_ids if sid in sources_by_id
            ) or "unknown source"
            lines.append(
                f"claim_id={c.claim_id} | agreement={c.agreement.value} | sources=[{src_desc}]\n"
                f"claim: {c.text}"
            )
        user = "Claims to judge:\n\n" + "\n\n".join(lines)
        try:
            data = await groq_client.complete_json(SYSTEM, user)
        except Exception:
            data = {"verdicts": []}

        returned = {v.get("claim_id"): v for v in data.get("verdicts", [])}
        for c in needs_review:
            v = returned.get(c.claim_id)
            if v and v.get("verdict") in VerdictLabel._value2member_map_:
                verdicts.append(
                    Verdict(
                        claim_id=c.claim_id,
                        verdict=VerdictLabel(v["verdict"]),
                        confidence=Confidence(v.get("confidence", "medium")) if v.get("confidence") in Confidence._value2member_map_ else Confidence.medium,
                        method="LLM cross-reference review",
                        notes=v.get("notes", ""),
                    )
                )
            else:
                # Defensive default if the model skipped a claim.
                verdicts.append(
                    Verdict(
                        claim_id=c.claim_id,
                        verdict=VerdictLabel.unverified,
                        confidence=Confidence.low,
                        method="fallback (no model judgement returned)",
                        notes="Could not be independently assessed.",
                    )
                )
    return verdicts
