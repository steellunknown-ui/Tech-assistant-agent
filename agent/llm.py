"""LLM Configuration & Provider Abstraction Module

Provides Large Language Model (LLM) configuration for the real-time voice agent.
Primary: Google Gemini Flash-Lite (temperature=0.3)
Fallback: Groq (temperature=0.3)
Integrated via LiveKit's FallbackAdapter for zero-downtime failover.
"""

import os
from livekit.agents import llm
from livekit.plugins import google, groq


def get_gemini_llm() -> llm.LLM:
    """Primary provider: Google Gemini Flash-Lite."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    thinking_level = os.getenv("GEMINI_THINKING_LEVEL", "unspecified").lower()

    thinking_config = None
    if thinking_level in ["minimal", "off"]:
        thinking_config = {"thinking_level": "minimal"}
    elif thinking_level == "low":
        thinking_config = {"thinking_level": "low"}

    kwargs = {
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "temperature": 0.3,
        "api_key": api_key if api_key else None,
    }
    if thinking_config:
        kwargs["thinking_config"] = thinking_config

    return google.LLM(**kwargs)


def get_groq_llm() -> llm.LLM:
    """Fallback provider: Groq high-speed inference."""
    api_key = os.getenv("GROQ_API_KEY")
    return groq.LLM(
        model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
        temperature=0.3,
        api_key=api_key if api_key else None,
    )


def get_llm(direct_groq: bool = False, direct_gemini: bool = False) -> llm.LLM:
    """Returns the configured LLM provider abstraction."""
    if direct_groq or os.getenv("LLM_PROVIDER", "").lower() == "groq":
        return get_groq_llm()

    if direct_gemini or os.getenv("LLM_PROVIDER", "").lower() == "gemini_direct":
        return get_gemini_llm()

    primary = get_gemini_llm()
    fallback = get_groq_llm()

    # Wrap in LiveKit FallbackAdapter for automatic seamless failover
    return llm.FallbackAdapter(
        llm=[primary, fallback],
        attempt_timeout=10.0,
        max_retry_per_llm=1,
        retry_interval=0.5,
    )
