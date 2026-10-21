"""STT Configuration Module

Provides streaming Speech-to-Text (STT) for the real-time voice agent.
To swap providers, change the returned STT instance in `get_stt()`.
"""

import os
from livekit.agents import stt
from livekit.plugins import deepgram


def get_stt() -> stt.STT:
    """Returns the configured streaming STT provider.

    Default: Deepgram Nova-3 Streaming STT (English)
    To swap in one line:
        return google.STT(languages=["en-US"])
        or return openai.STT()
    """
    api_key = os.getenv("DEEPGRAM_API_KEY")
    return deepgram.STT(
        model=os.getenv("DEEPGRAM_MODEL", "nova-3"),
        language="en-US",
        punctuate=True,
        interim_results=True,
        api_key=api_key if api_key else None,
    )
