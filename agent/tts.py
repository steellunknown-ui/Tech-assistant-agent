"""TTS Configuration Module

Provides streaming Text-to-Speech (TTS) for the real-time voice agent.
Supports:
1. Cartesia Sonic AI (via livekit-plugins-cartesia) using CARTESIA_API_KEY (~100ms TTFB, hyper-realistic human voice)
2. Direct Fish Audio (via livekit-plugins-fishaudio) using FISH_API_KEY
3. Seamless FallbackAdapter: automatically falls back to Deepgram Aura if Cartesia runs out of credits
"""

import os
import logging
from livekit.agents import tts
from livekit.plugins import cartesia, deepgram

logger = logging.getLogger("tts-provider")


def get_tts() -> tts.TTS:
    """Returns the configured streaming TTS provider with automatic fallback."""
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    fish_key = os.getenv("FISH_API_KEY")
    dg_key = os.getenv("DEEPGRAM_API_KEY")

    # Base fallback: Deepgram Aura (Male Voice: aura-orion-en)
    fallback_dg = deepgram.TTS(
        model=os.getenv("DEEPGRAM_TTS_MODEL", "aura-orion-en"),
        api_key=dg_key if dg_key else None,
    )

    tts_chain = []

    # Tier 1: Cartesia Account 1 (Primary Cloned Voice)
    if cartesia_key:
        voice_id = os.getenv("CARTESIA_VOICE_ID", "b4a7492e-52bc-4626-b097-876593589fbd")
        model = os.getenv("CARTESIA_MODEL", "sonic-3")
        logger.info(f"Tier 1: Cartesia Account 1 (Model: {model}, Voice: {voice_id})")
        tts_chain.append(
            cartesia.TTS(
                api_key=cartesia_key,
                model=model,
                voice=voice_id,
            )
        )

    # Tier 2: Cartesia Account 2 (Secondary Cloned Voice Fallback)
    cartesia_key_2 = os.getenv("CARTESIA_API_KEY_2")
    if cartesia_key_2:
        voice_id_2 = os.getenv("CARTESIA_VOICE_ID_2", "df52583d-c843-489f-a413-79bf17ceb806")
        model = os.getenv("CARTESIA_MODEL", "sonic-3")
        logger.info(f"Tier 2: Cartesia Account 2 (Model: {model}, Voice: {voice_id_2})")
        tts_chain.append(
            cartesia.TTS(
                api_key=cartesia_key_2,
                model=model,
                voice=voice_id_2,
            )
        )

    # Tier 3: Deepgram Orion Male Voice (Final Resilience Safety Net)
    tts_chain.append(fallback_dg)

    logger.info(f"Configured 3-Tier Chained TTS: {[t.label for t in tts_chain]}")
    adapter = tts.FallbackAdapter(
        tts=tts_chain,
        max_retry_per_tts=1,
    )

    @adapter.on("tts_availability_changed")
    def _on_tts_avail(ev):
        logger.warning(f"[TTS FallbackAdapter] Failover event: {ev}")

    return adapter

    # Priority 2: Direct Fish Audio if configured
    if fish_key:
        try:
            from livekit.plugins import fishaudio
            voice_id = os.getenv("FISH_AUDIO_VOICE_ID", "a204d00fe33d4613bc7737a39323201c")
            logger.info(f"Using Fish Audio TTS (Voice: {voice_id}) with Deepgram fallback")
            fish_tts = fishaudio.TTS(
                model=os.getenv("FISH_AUDIO_MODEL", "s2.1-pro"),
                latency_mode=os.getenv("FISH_LATENCY_MODE", "balanced"),
                api_key=fish_key,
                voice_id=voice_id,
            )
            return tts.FallbackAdapter(
                tts=[fish_tts, fallback_dg],
                max_retry_per_tts=1,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Fish Audio TTS: {e}")

    return fallback_dg
