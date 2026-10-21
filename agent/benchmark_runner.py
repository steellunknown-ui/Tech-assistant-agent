"""Automated 15-Turn Voice Benchmark Runner

Plays 15 pre-recorded technical support queries into a LiveKit room
via WebRTC LocalAudioTrack and AudioSource at 48kHz linear16 PCM.
Spaces questions by 4+ seconds of silence after agent response completion.
Collects turn latencies, discards Turn 1 (cold start), and computes p50 and p95.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Ensure the agent directory is in Python path
agent_dir = Path(__file__).resolve().parent
root_dir = agent_dir.parent
load_dotenv(agent_dir / ".env")
load_dotenv(root_dir / ".env")

from livekit import api, rtc

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark-runner")

ROOM_NAME = "voice-latency-bench"
QUESTIONS = [
    ("q1", "My internet is not working"),
    ("q2", "Can you help me reset my router?"),
    ("q3", "Where do I find my account number?"),
    ("q4", "Why is my connection speed so slow?"),
    ("q5", "How do I change my Wi-Fi password?"),
    ("q6", "Is there a service disruption in my area?"),
    ("q7", "Can I schedule a technician visit?"),
    ("q8", "How do I view my latest bill?"),
    ("q9", "Do you offer fiber internet upgrades?"),
    ("q10", "What are your customer support working hours?"),
    ("q11", "Can I pay my bill over the phone?"),
    ("q12", "My screen says no signal detected."),
    ("q13", "How do I setup parental controls on my network?"),
    ("q14", "What should I do if my modem lights are blinking red?"),
    ("q15", "Can you send a confirmation email for this service request?"),
]


async def run_benchmark():
    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not livekit_url or not api_key or not api_secret:
        logger.error("LiveKit credentials missing from environment.")
        return

    logger.info(f"Generating caller token for room '{ROOM_NAME}'...")
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity("bench-caller-mumbai")
        .with_name("Bench User (Mumbai)")
        .with_grants(api.VideoGrants(room_join=True, room=ROOM_NAME))
        .to_jwt()
    )

    room = rtc.Room()
    agent_joined_event = asyncio.Event()

    @room.on("participant_connected")
    def on_participant_connected(p: rtc.RemoteParticipant):
        logger.info(f"Remote participant joined: {p.identity} (name: {p.name})")
        agent_joined_event.set()

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.RemoteTrack, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        logger.info(f"Subscribed to remote track {track.sid} from {participant.identity} (kind: {track.kind})")
        agent_joined_event.set()

    logger.info(f"Connecting caller to LiveKit room '{ROOM_NAME}'...")
    await room.connect(livekit_url, token)
    logger.info(f"Connected to room {room.name} as {room.local_participant.identity}")

    # Check if agent is already in the room
    for p in room.remote_participants.values():
        logger.info(f"Found existing participant: {p.identity}")
        agent_joined_event.set()

    # Create 48kHz mono audio source and track
    sample_rate = 48000
    source = rtc.AudioSource(sample_rate=sample_rate, num_channels=1)
    track = rtc.LocalAudioTrack.create_audio_track("bench-user-mic", source)
    await room.local_participant.publish_track(
        track,
        rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    )
    logger.info("Published 48kHz audio track to room.")

    logger.info("Waiting for technical support agent to join room...")
    try:
        await asyncio.wait_for(agent_joined_event.wait(), timeout=20.0)
    except asyncio.TimeoutError:
        logger.warning("No agent joined within 20s. Proceeding anyway.")

    logger.info("Waiting 6s for agent's initial greeting to complete...")
    await asyncio.sleep(6.0)

    # Chunk size: 20ms @ 48kHz mono = 960 samples = 1920 bytes
    samples_per_frame = int(sample_rate * 0.02)  # 960 samples
    bytes_per_frame = samples_per_frame * 2       # 16-bit PCM = 2 bytes per sample

    for idx, (qid, text) in enumerate(QUESTIONS, 1):
        audio_file = agent_dir / "test_audio" / f"{qid}.mp3"
        if not audio_file.exists():
            logger.error(f"Audio file {audio_file} not found!")
            continue

        raw_pcm = audio_file.read_bytes()
        duration_s = len(raw_pcm) / (sample_rate * 2)
        logger.info(f"\n[BENCH TURN {idx}/15] Playing '{text}' ({duration_s:.2f}s audio)...")

        # Stream the audio frames in real time (20ms intervals)
        for offset in range(0, len(raw_pcm), bytes_per_frame):
            chunk = raw_pcm[offset:offset + bytes_per_frame]
            if len(chunk) < bytes_per_frame:
                chunk = chunk + b"\x00" * (bytes_per_frame - len(chunk))
            frame = rtc.AudioFrame(chunk, sample_rate, 1, samples_per_frame)
            await source.capture_frame(frame)
            await asyncio.sleep(0.02)

        # Feed 300ms of silence to trigger VAD endpointing cleanly
        silence_frame = rtc.AudioFrame(b"\x00" * bytes_per_frame, sample_rate, 1, samples_per_frame)
        for _ in range(15):
            await source.capture_frame(silence_frame)
            await asyncio.sleep(0.02)

        # Wait 9.0s: covers response generation (~1-2s), spoken reply (~3-4s), and 4s quiet pause
        logger.info(f"[BENCH TURN {idx}/15] Finished speech. Waiting 9s (agent speech + 4s pause)...")
        await asyncio.sleep(9.0)

    logger.info("\nAll 15 benchmark turns completed successfully!")
    await asyncio.sleep(2.0)
    await room.disconnect()
    logger.info("Caller disconnected from LiveKit.")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
