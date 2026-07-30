import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    groq_max_concurrency: int = int(os.getenv("GROQ_MAX_CONCURRENCY", "3"))
    search_max_concurrency: int = int(os.getenv("SEARCH_MAX_CONCURRENCY", "5"))
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # Research tuning knobs, keyed by "depth" level chosen in the UI.
    depth_presets = {
        "quick": {"sub_questions": 3, "sources_per_question": 3},
        "standard": {"sub_questions": 5, "sources_per_question": 4},
        "deep": {"sub_questions": 7, "sources_per_question": 6},
    }


settings = Settings()
