import asyncio
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

from .config import settings
from .schemas import SearchResult, SourceType

_search_semaphore = asyncio.Semaphore(settings.search_max_concurrency)

# Domains that are reliably low signal-to-noise for research purposes.
LOW_QUALITY_DOMAINS = {
    "pinterest.com", "quora.com", "answers.com", "yahoo.com",
    "ask.com", "slideshare.net",
}

ACADEMIC_HINTS = (".edu", "arxiv.org", "ncbi.nlm.nih.gov", "jstor.org", "nature.com", "sciencedirect.com")
OFFICIAL_HINTS = (".gov", ".int", "who.int", "un.org")
NEWS_HINTS = (
    "reuters.com", "apnews.com", "bbc.", "nytimes.com", "wsj.com", "bloomberg.com",
    "theguardian.com", "npr.org", "economist.com", "ft.com",
)
REFERENCE_HINTS = ("wikipedia.org", "britannica.com")


def _domain_of(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""


def _classify_source(domain: str) -> SourceType:
    if any(h in domain for h in ACADEMIC_HINTS):
        return SourceType.academic
    if any(h in domain for h in OFFICIAL_HINTS):
        return SourceType.official
    if any(h in domain for h in NEWS_HINTS):
        return SourceType.news
    if any(h in domain for h in REFERENCE_HINTS):
        return SourceType.reference
    if any(k in domain for k in ("blog", "medium.com", "reddit.com", "forum")):
        return SourceType.blog_or_forum
    return SourceType.other


def _quality_score(domain: str, source_type: SourceType) -> float:
    if domain in LOW_QUALITY_DOMAINS:
        return 0.15
    base = {
        SourceType.official: 0.95,
        SourceType.academic: 0.92,
        SourceType.news: 0.8,
        SourceType.reference: 0.7,
        SourceType.other: 0.55,
        SourceType.blog_or_forum: 0.35,
    }[source_type]
    return base


async def web_search(query: str, max_results: int = 6) -> list[dict]:
    """Run a DuckDuckGo text search. Blocking library, so we push it to a thread."""
    def _run():
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))

    async with _search_semaphore:
        return await asyncio.to_thread(_run)


async def fetch_page_text(url: str, max_chars: int = 6000) -> str:
    """Fetch a URL and extract readable body text, best-effort."""
    try:
        async with _search_semaphore:
            async with httpx.AsyncClient(
                timeout=12,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (research-assistant-crew)"},
            ) as client:
                resp = await client.get(url)
        if resp.status_code >= 400 or "text/html" not in resp.headers.get("content-type", ""):
            return ""
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 40)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""


async def search_and_fetch(sub_question_id: str, query: str, max_results: int) -> list[SearchResult]:
    """One end-to-end search round for a sub-question: search, classify,
    dedupe by domain, and fetch page bodies for the top hits in parallel.
    """
    raw_results = await web_search(query, max_results=max_results * 2)

    seen_domains: set[str] = set()
    candidates = []
    for r in raw_results:
        url = r.get("href") or r.get("url") or ""
        if not url:
            continue
        domain = _domain_of(url)
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)
        candidates.append((url, domain, r))
        if len(candidates) >= max_results:
            break

    async def build(idx: int, url: str, domain: str, raw: dict) -> SearchResult:
        source_type = _classify_source(domain)
        content = await fetch_page_text(url)
        return SearchResult(
            source_id=f"{sub_question_id}-s{idx}",
            sub_question_id=sub_question_id,
            url=url,
            title=raw.get("title", domain),
            domain=domain,
            source_type=source_type,
            snippet=raw.get("body", "")[:400],
            content=content or raw.get("body", ""),
            quality_score=_quality_score(domain, source_type),
        )

    results = await asyncio.gather(
        *[build(i, u, d, r) for i, (u, d, r) in enumerate(candidates)]
    )
    # Surface the highest-quality sources first.
    return sorted(results, key=lambda r: r.quality_score, reverse=True)
