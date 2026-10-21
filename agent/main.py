"""Real-Time Technical Support Voice Agent (Phase 1 & Phase 2 Benchmarking)

Minimal voice agent built with LiveKit Agents v1.8.8.
- STT: Deepgram streaming STT (English)
- LLM: Google Gemini Flash-Lite (temp 0.3) with Groq fallback
- TTS: Deepgram Aura / Fish Audio streaming TTS
- Persona: Professional technical support engineer (max 2 sentences, English only)
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Ensure the agent directory is in Python path
agent_dir = Path(__file__).resolve().parent
root_dir = agent_dir.parent
if str(agent_dir) not in sys.path:
    sys.path.insert(0, str(agent_dir))

# Load environment variables
load_dotenv(agent_dir / ".env")
load_dotenv(root_dir / ".env")

from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import cartesia, silero

from stt import get_stt
from llm import get_llm
from tts import get_tts

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tech-support-agent")

SUPPORT_PERSONA_INSTRUCTIONS = """You are an experienced male technical support engineer assisting a user over real-time voice.
Your tone is calm, polite, and confident.
You speak English only.

CRITICAL VOICE INSTRUCTIONS:
1. Speak concisely: your response MUST be a MAXIMUM OF 2 SHORT SENTENCES. Never exceed two sentences.
2. Provide one clear troubleshooting action or ask one targeted clarifying question at a time.
3. This is spoken voice: do NOT use markdown, lists, asterisks, URLs, code blocks, or emojis.
4. Keep the pace conversational and focused on resolving the user's issue.
"""


async def entrypoint(ctx: JobContext):
    """Entrypoint executed when an agent worker takes a room job."""
    logger.info(f"Connecting to LiveKit room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Initialize modular providers (STT, LLM with fallback, TTS)
    stt_provider = get_stt()
    llm_provider = get_llm()
    tts_provider = get_tts()
    vad_provider = silero.VAD.load()
    logger.info(f"Active TTS provider initialized: {getattr(tts_provider, 'model', tts_provider)}")

    # Configurable turn handling options for benchmarking
    min_endpointing_delay = float(os.getenv("MIN_ENDPOINTING_DELAY", "0.7"))
    max_endpointing_delay = float(os.getenv("MAX_ENDPOINTING_DELAY", "2.5"))
    preemptive = os.getenv("PREEMPTIVE_GENERATION", "false").lower() == "true"
    preemptive_tts = os.getenv("PREEMPTIVE_TTS", "false").lower() == "true"
    interruption_mode = os.getenv("INTERRUPTION_MODE", "adaptive").lower()

    turn_handling_cfg = {
        "endpointing": {
            "min_delay": min_endpointing_delay,
            "max_delay": max_endpointing_delay,
        },
        "preemptive_generation": {
            "enabled": preemptive,
            "preemptive_tts": preemptive_tts,
        },
        "interruption": {
            "enabled": True,
            "mode": interruption_mode,
            "min_duration": 0.5,
            "min_words": 2,
            "resume_false_interruption": True,
        },
    }

    # Create the LiveKit 1.8 AgentSession pipeline
    session = AgentSession(
        vad=vad_provider,
        stt=stt_provider,
        llm=llm_provider,
        tts=tts_provider,
        turn_handling=turn_handling_cfg,
    )

    # Instantiate the agent persona definition
    support_agent = Agent(
        instructions=SUPPORT_PERSONA_INSTRUCTIONS,
    )

    # Per-turn metrics tracker
    last_user_metrics = {}
    turn_metrics_map = {}
    turn_counter = 0

    @session.on("metrics_collected")
    def on_metrics_collected(ev: agents.MetricsCollectedEvent):
        m = ev.metrics
        sid = getattr(m, "speech_id", None) or "active"
        if sid not in turn_metrics_map:
            turn_metrics_map[sid] = {}
        data = turn_metrics_map[sid]

        from livekit.agents.metrics import EOUMetrics, STTMetrics, LLMMetrics, TTSMetrics
        if isinstance(m, EOUMetrics):
            data["eou_delay"] = m.end_of_utterance_delay
            data["stt_delay"] = m.transcription_delay
        elif isinstance(m, STTMetrics):
            data["stt_duration"] = m.duration
        elif isinstance(m, LLMMetrics):
            data["llm_ttft"] = m.ttft
            data["reasoning_tokens"] = getattr(m, "reasoning_tokens", 0)
        elif isinstance(m, TTSMetrics):
            data["tts_ttfb"] = m.ttfb

    @session.on("conversation_item_added")
    def on_conversation_item_added(ev: agents.ConversationItemAddedEvent):
        nonlocal last_user_metrics, turn_counter
        item = ev.item
        if not isinstance(item, agents.llm.ChatMessage):
            return

        if item.role == "user":
            last_user_metrics = item.metrics or {}
        elif item.role == "assistant":
            asst_metrics = item.metrics or {}
            e2e = asst_metrics.get("e2e_latency")

            u = last_user_metrics or {}
            eou_s = u.get("end_of_turn_delay") or 0.0
            stt_s = u.get("transcription_delay") or 0.0
            ttft_s = asst_metrics.get("llm_node_ttft") or 0.0
            ttfb_s = asst_metrics.get("tts_node_ttfb") or 0.0

            # Compute real E2E from LiveKit metrics
            # Note: EOU and STT delay overlap (both start from last_speaking_time).
            # The true elapsed time before LLM begins is max(EOU, STT).
            if e2e is not None and e2e > 0:
                real_e2e_ms = e2e * 1000
            else:
                real_e2e_ms = (max(eou_s, stt_s) + ttft_s + ttfb_s) * 1000

            text = item.text_content.replace("\n", " ").strip()
            model_name = os.getenv("LLM_PROVIDER", os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"))
            thinking_env = os.getenv("GEMINI_THINKING_LEVEL", "default dynamic")

            # Only log user conversation turns (ignore initial greeting where e2e/eou == 0)
            if real_e2e_ms > 0 or eou_s > 0 or stt_s > 0:
                turn_counter += 1
                print(
                    f"[TURN {turn_counter}] Real E2E: {real_e2e_ms:.1f}ms | "
                    f"EOU: {eou_s*1000:.1f}ms | STT: {stt_s*1000:.1f}ms | "
                    f"LLM TTFT: {ttft_s*1000:.1f}ms | TTS TTFB: {ttfb_s*1000:.1f}ms | "
                    f"Model: {model_name} | Thinking: {thinking_env} | "
                    f'LLM: "{text}"',
                    flush=True,
                )

    # Start session within the connected room
    await session.start(support_agent, room=ctx.room)

    # Generate an instant initial spoken greeting via TTS directly
    await session.say("Hello, welcome to technical support! How can I help you today?")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
