from ..groq_client import groq_client
from ..schemas import SubQuestion, SearchResult
from ..search_tools import search_and_fetch

SYSTEM = """You turn a research sub-question into one effective, specific web \
search engine query. Keep it short (under 12 words), use concrete keywords, \
avoid filler words like "what is" when a keyword phrase would search better. \
Respond with ONLY a JSON object: {"query": "..."}"""


async def _build_search_query(sub_question: SubQuestion) -> str:
    try:
        data = await groq_client.complete_json(SYSTEM, f"Sub-question: {sub_question.text}")
        q = (data.get("query") or "").strip()
        return q or sub_question.text
    except Exception:
        return sub_question.text


async def run_search_agent(sub_question: SubQuestion, sources_per_question: int) -> list[SearchResult]:
    query = await _build_search_query(sub_question)
    results = await search_and_fetch(sub_question.id, query, sources_per_question)
    return results
