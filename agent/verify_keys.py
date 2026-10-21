"""API Key Verification & Diagnostic Tool

Allows testing each provider's API key individually or all at once.
Usage:
    python verify_keys.py --provider [openrouter|gemini|groq|deepgram|livekit|all]
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Load .env from agent dir or project root
agent_dir = Path(__file__).resolve().parent
load_dotenv(agent_dir / ".env")
load_dotenv(agent_dir.parent / ".env")


async def test_openrouter():
    print("\n--- [1/5] Testing OpenRouter Fish Audio (s2.1-pro-free:free) ---")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY is not set in .env.")
        return False

    import httpx
    model = os.getenv("OPENROUTER_FISH_MODEL", "fish-audio/s2.1-pro-free:free")
    voice_id = os.getenv("FISH_AUDIO_VOICE_ID", "a204d00fe33d4613bc7737a39323201c")  # Homelander default
    url = "https://openrouter.ai/api/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": "Technical support online. I am here to help you resolve your issue.",
        "voice": voice_id,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200 and len(res.content) > 0:
                print(f"✅ OpenRouter Fish Audio success! Received {len(res.content)} bytes.")
                print(f"   Model: {model}")
                print(f"   Voice ID (Homelander): {voice_id}")
                return True
            else:
                print(f"❌ OpenRouter error ({res.status_code}): {res.text}")
                return False
    except Exception as e:
        print(f"❌ Failed to reach OpenRouter: {e}")
        return False


async def test_gemini():
    print("\n--- [2/5] Testing Google Gemini Flash ---")
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY is not set in .env.")
        return False

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        response = client.models.generate_content(
            model=model,
            contents="Respond with only the word: ONLINE",
        )
        print(f"✅ Google Gemini Flash ({model}) success! Response: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"❌ Google Gemini Flash error: {e}")
        return False


async def test_groq():
    print("\n--- [3/5] Testing Groq Fallback LLM ---")
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY is not set in .env.")
        return False

    import httpx
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Respond with only the word: ONLINE"}],
        "temperature": 0.3,
        "max_tokens": 10,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                reply = data["choices"][0]["message"]["content"].strip()
                print(f"✅ Groq ({model}) success! Response: {reply}")
                return True
            else:
                print(f"❌ Groq error ({res.status_code}): {res.text}")
                return False
    except Exception as e:
        print(f"❌ Groq connection error: {e}")
        return False


async def test_deepgram():
    print("\n--- [4/5] Testing Deepgram Streaming STT ---")
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("❌ DEEPGRAM_API_KEY is not set in .env.")
        return False

    import httpx
    # 1. Test listen endpoint with a tiny WAV silence header
    # 44-byte minimal WAV header of silence
    wav_header = (
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    url = "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true"
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/wav",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, headers=headers, content=wav_header)
            if res.status_code == 200:
                print("✅ Deepgram Streaming STT validated successfully! Ready for real-time transcription.")
                return True
            else:
                # Fallback check projects endpoint
                res_proj = await client.get("https://api.deepgram.com/v1/projects", headers={"Authorization": f"Token {api_key}"})
                if res_proj.status_code == 200:
                    print("✅ Deepgram key validated successfully via projects API.")
                    return True
                print(f"❌ Deepgram error ({res.status_code}): {res.text}")
                return False
    except Exception as e:
        print(f"❌ Deepgram connection error: {e}")
        return False


async def test_livekit():
    print("\n--- [5/5] Testing LiveKit Cloud Credentials ---")
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not url or not api_key or not api_secret:
        print("❌ LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET is missing.")
        return False

    try:
        from livekit import api
        lkapi = api.LiveKitAPI(url, api_key, api_secret)
        rooms = await lkapi.room.list_rooms(api.ListRoomsRequest())
        await lkapi.aclose()
        print(f"✅ LiveKit Cloud authenticated successfully! Active rooms: {len(rooms.rooms)}")
        return True
    except Exception as e:
        print(f"❌ LiveKit connection error: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description="Verify Voice Agent API Keys")
    parser.add_argument(
        "--provider",
        choices=["openrouter", "gemini", "groq", "deepgram", "livekit", "all"],
        default="all",
        help="Specific provider key to test",
    )
    args = parser.parse_args()

    tests = {
        "openrouter": test_openrouter,
        "gemini": test_gemini,
        "groq": test_groq,
        "deepgram": test_deepgram,
        "livekit": test_livekit,
    }

    if args.provider == "all":
        results = {}
        for name, test_fn in tests.items():
            results[name] = await test_fn()
        print("\n================ SUMMARY ================")
        for name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL / UNCONFIGURED"
            print(f"{name.upper():<12}: {status}")
    else:
        await tests[args.provider]()


if __name__ == "__main__":
    asyncio.run(main())
