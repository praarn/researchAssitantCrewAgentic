from ..groq_client import groq_client
from ..schemas import ResearchPlan, SubQuestion, Depth, Audience
from ..config import settings

SYSTEM = """You are the Planner agent in a research pipeline. You take a raw \
user question and turn it into a small set of precise, independently \
searchable sub-questions that together fully cover what the user is asking. \

Rules:
- Sub-questions must be concrete and searchable (good for a web search engine), not vague.
- Avoid overlap between sub-questions - each should cover distinct ground.
- Order sub-questions from most foundational to most nuanced.
- Respond with ONLY a JSON object matching this shape:
{
  "restated_goal": "one or two sentences restating what the user actually wants to learn",
  "sub_questions": [
    {"text": "...", "rationale": "why this sub-question matters, one short clause"}
  ]
}
"""


async def run_planner(query: str, depth: Depth, audience: Audience) -> ResearchPlan:
    n = settings.depth_presets[depth.value]["sub_questions"]
    user = (
        f"User question: {query}\n"
        f"Audience for the final report: {audience.value}\n"
        f"Produce exactly {n} sub-questions."
    )
    data = await groq_client.complete_json(SYSTEM, user)
    sub_qs = data.get("sub_questions", [])[:n]
    sub_questions = [
        SubQuestion(id=f"q{i+1}", text=sq.get("text", "").strip(), rationale=sq.get("rationale", ""))
        for i, sq in enumerate(sub_qs)
        if sq.get("text")
    ]
    if not sub_questions:
        # Defensive fallback so the pipeline never dead-ends on a bad model response.
        sub_questions = [SubQuestion(id="q1", text=query, rationale="Direct lookup of the original question")]
    return ResearchPlan(
        main_query=query,
        restated_goal=data.get("restated_goal", query),
        sub_questions=sub_questions,
    )
