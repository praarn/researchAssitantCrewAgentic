import json
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqError(Exception):
    pass


class RateLimited(GroqError):
    pass


class GroqClient:
    """Thin async wrapper around Groq's OpenAI-compatible chat completions
    endpoint. Every agent in this app goes through here, and only here -
    this is the single integration point with an external LLM provider.
    """

    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.groq_max_concurrency)

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1.5, min=1, max=20),
        retry=retry_if_exception_type(RateLimited),
    )
    async def _post(self, payload: dict) -> dict:
        if not settings.groq_api_key:
            raise GroqError(
                "GROQ_API_KEY is not set. Add it to backend/.env - "
                "get a free key at https://console.groq.com/keys"
            )
        headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        async with self._semaphore:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(GROQ_URL, headers=headers, json=payload)
        if resp.status_code == 429:
            raise RateLimited("Groq rate limit hit, backing off")
        if resp.status_code >= 400:
            raise GroqError(f"Groq API error {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    def _base_payload(self, temperature: float, reasoning_effort: str) -> dict:
        payload = {"model": settings.groq_model, "temperature": temperature}
        if settings.groq_model.startswith("openai/gpt-oss"):
            payload["reasoning_effort"] = reasoning_effort
        return payload

    async def complete_json(self, system: str, user: str, temperature: float = 0.2, reasoning_effort: str = "low") -> dict:
        """Call Groq asking for a strict JSON object response, and parse it."""
        payload = {
            **self._base_payload(temperature, reasoning_effort),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = await self._post(payload)
        raw = data["choices"][0]["message"]["content"]
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise GroqError(f"Model did not return valid JSON: {e}\nRaw: {raw[:500]}")

    async def complete_text(self, system: str, user: str, temperature: float = 0.4, reasoning_effort: str = "low") -> str:
        payload = {
            **self._base_payload(temperature, reasoning_effort),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        data = await self._post(payload)
        return data["choices"][0]["message"]["content"]


groq_client = GroqClient()
