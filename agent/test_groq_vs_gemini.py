import os
import time
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI
from google import genai
from google.genai import types

prompts = [
    "Hello, my Wi-Fi is not connecting on my phone. What should I check first?",
    "How do I reset my router to factory settings?",
    "Can you check if there is an internet outage in my area?",
    "Why are the modem lights blinking red?",
    "Can you help me resolve an issue with my laptop screen brightness?",
]

def test_groq(model_name="qwen/qwen3.8-27b"):
    api_key = os.getenv("GROQ_API_KEY")
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    print(f"\n--- Testing Groq ({model_name}) ---")
    ttfts = []
    for p in prompts:
        t0 = time.time()
        res = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are technical support. Respond concisely in max 2 sentences."},
                {"role": "user", "content": p}
            ],
            temperature=0.3,
            stream=True
        )
        first_ttft = None
        text = []
        for chunk in res:
            if chunk.choices and chunk.choices[0].delta.content:
                if first_ttft is None:
                    first_ttft = (time.time() - t0) * 1000
                text.append(chunk.choices[0].delta.content)
        total_time = (time.time() - t0) * 1000
        ttfts.append(first_ttft)
        print(f"TTFT: {first_ttft:6.1f}ms | Total: {total_time:6.1f}ms | Reply: {''.join(text).strip()[:65]}...")
    return ttfts

def test_gemini(model_name="gemini-3.5-flash-lite"):
    api_key = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)
    print(f"\n--- Testing Google Gemini ({model_name}, minimal thinking) ---")
    ttfts = []
    config = types.GenerateContentConfig(
        temperature=0.3,
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
        system_instruction="You are technical support. Respond concisely in max 2 sentences."
    )
    for p in prompts:
        for attempt in range(3):
            try:
                t0 = time.time()
                res = client.models.generate_content_stream(
                    model=model_name,
                    contents=p,
                    config=config
                )
                first_ttft = None
                text = []
                for chunk in res:
                    if chunk.text:
                        if first_ttft is None:
                            first_ttft = (time.time() - t0) * 1000
                        text.append(chunk.text)
                total_time = (time.time() - t0) * 1000
                ttfts.append(first_ttft)
                print(f"TTFT: {first_ttft:6.1f}ms | Total: {total_time:6.1f}ms | Reply: {''.join(text).strip()[:65]}...")
                break
            except Exception as e:
                print(f"Gemini attempt {attempt+1} failed ({e}), retrying in 1s...")
                time.sleep(1.0)
    return ttfts

if __name__ == "__main__":
    groq_ttfts = test_groq("qwen/qwen3.8-27b")
    gemini_ttfts = test_gemini("gemini-3.5-flash-lite")

    import numpy as np
    print("\n================ SUMMARY COMPARISON ================")
    print(f"Groq   (qwen3.8-27b)        TTFT p50: {np.median(groq_ttfts):.1f}ms | p95: {np.percentile(groq_ttfts, 95):.1f}ms")
    print(f"Gemini (3.5-flash-lite)     TTFT p50: {np.median(gemini_ttfts):.1f}ms | p95: {np.percentile(gemini_ttfts, 95):.1f}ms")
