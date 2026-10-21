# Phase 1 Architectural & Technical Decisions

This document details the architectural decisions, component trade-offs, and provider abstractions implemented in Phase 1 of the Real-Time Technical Support Voice Agent.

---

## 1. System Overview & Architecture

The system consists of two primary runtime layers:
1. **Agent Worker (`agent/`)**: A Python background worker process using the `livekit-agents` framework that connects to LiveKit rooms, subscribes to client audio, orchestrates VAD, STT, LLM inference with fallback, and streams TTS back to the client.
2. **Web Client (`web/`)**: A Next.js web application utilizing `livekit-client` and `@livekit/components-react` / pure WebRTC audio track listeners. It provides an intuitive interface with a Connect/Disconnect toggle, microphone permission control, and real-time state visualization (**Listening**, **Thinking**, **Speaking**).

```
[ User Microphone ] 
       │ (WebRTC Audio)
       ▼
 [ LiveKit Server / Cloud ]
       │ (Dispatches Room Job)
       ▼
 [ agent/main.py (Agent Worker) ]
   ├── VAD: Silero VAD (voice activity detection)
   ├── STT: Deepgram Streaming STT (Nova-3, English)
   ├── LLM: Provider Abstraction
   │     ├── Primary: Google Gemini Flash (temp: 0.3)
   │     └── Fallback: Groq Llama-3.3-70B / 3.1-8B (temp: 0.3)
   └── TTS: Fish Audio Streaming TTS (s2.1-pro, swappable)
       │ (WebRTC Audio Track)
       ▼
 [ User Headphones / Speaker ]
```

---

## 2. Voice Pipeline & Provider Decisions

### 2.1 Speech-to-Text (STT): Deepgram Streaming
- **Provider**: Deepgram (`livekit-plugins-deepgram`)
- **Model**: `nova-3` (with `nova-2` support), language set to `en`.
- **Rationale**: Deepgram streaming STT provides industry-leading word-error-rate (WER) under noisy microphone conditions with sub-300ms time-to-first-transcript. Its streaming endpoint integrates natively with LiveKit VAD to emit final transcript events immediately upon end-of-speech.
- **Config Isolation**: Isolated in [`agent/stt.py`](file:///d:/Technical-assitant%20agent/agent/stt.py) (`get_stt()`), swappable in a single line.

### 2.2 LLM: Primary Google Gemini Flash with Groq Fallback
- **Primary Model**: Google Gemini Flash (e.g. `gemini-2.5-flash` or `gemini-1.5-flash`) via `livekit-plugins-google`.
- **Fallback Model**: Groq (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`) via `livekit-plugins-groq`.
- **Temperature**: `0.3` for both providers. Low temperature ensures deterministic, hallucination-resistant, concise, and logically consistent technical troubleshooting advice.
- **Failover Mechanism**: Uses LiveKit's `FallbackAdapter` (`livekit.agents.llm.FallbackAdapter`), wrapping the primary Google Gemini LLM and secondary Groq LLM. If Gemini hits rate limits (HTTP 429), timeouts, or API errors, the adapter immediately routes the turn to Groq without crashing the live call.
- **Config Isolation**: Encapsulated in [`agent/llm.py`](file:///d:/Technical-assitant%20agent/agent/llm.py) (`get_llm()`).

### 2.3 Text-to-Speech (TTS): Fish Audio Streaming
- **Provider**: Fish Audio (`livekit-plugins-fishaudio`)
- **Model**: `s2.1-pro`, `latency_mode="balanced"`, streaming PCM audio chunks.
- **Rationale**: Fish Audio delivers expressive, low-latency synthesized speech.
- **Modularity & Swappability**: Encapsulated in [`agent/tts.py`](file:///d:/Technical-assitant%20agent/agent/tts.py) (`get_tts()`). If a user wishes to switch to Cartesia, ElevenLabs, Deepgram Aura, or LiveKit Inference, the change is strictly one line in `agent/tts.py`.

---

## 3. Persona & Spoken Style Constraints

- **Language**: English only (`en-US`).
- **Response Length**: Strictly **maximum 2 sentences per response**. Spoken voice agents fail when producing lengthy paragraphs because users cannot retain or interrupt long soliloquies comfortably.
- **Persona**: Calm, highly competent, professional Tier-2 Technical Support Engineer. Acknowledges user issues succinctly, asks one clarifying question at a time, or provides one direct troubleshooting action.
- **Prompt Guardrails**: Explicit instructions in the system prompt enforce:
  1. No markdown, bullet points, asterisks, or code fences in speech output.
  2. Spoken numbers and terms spelled naturally (e.g., "dot" instead of periods in URLs when helpful).
  3. No filler introductions like "As an AI language model...".

---

## 4. Web Client Architecture

- **Framework**: Next.js 14 (App Router) + TypeScript.
- **WebRTC Client**: `livekit-client` v2.x.
- **Token Generation**: Next.js API route (`/api/token`) uses `livekit-server-sdk` with `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` to mint participant tokens securely on demand.
- **Styling**: Vanilla CSS (`app/globals.css`) designed with a modern dark glassmorphism design system. Avoids external CSS frameworks (like Tailwind) for clean, predictable, zero-dependency styling.
- **Agent State Indicators**:
  - **Listening**: User is speaking (local microphone audio detected via audio track / VAD).
  - **Thinking**: Agent received user transcript and is awaiting the first audio/text packet from the LLM/TTS pipeline.
  - **Speaking**: Remote agent audio track is currently unmuted and actively playing audio through the client speakers.

---

## 5. Pinned Dependency Versions

All core dependencies are pinned in `agent/requirements.txt` and `web/package.json` to prevent drift across updates:

### Python Agent (`agent/requirements.txt`)
- `livekit-agents==1.8.8`
- `livekit-plugins-deepgram==1.8.8`
- `livekit-plugins-google==1.8.8`
- `livekit-plugins-groq==1.8.8`
- `livekit-plugins-fishaudio==1.8.8`
- `livekit-plugins-silero==1.8.8`
- `python-dotenv==1.1.1`

### Web Client (`web/package.json`)
- `next`: `14.2.25`
- `react`: `18.3.1`
- `react-dom`: `18.3.1`
- `livekit-client`: `2.23.0`
- `livekit-server-sdk`: `2.19.1`
- `typescript`: `5.7.3`

---

## 6. Exclusions in Phase 1

As specified in the Phase 1 scope:
- **No RAG**: Knowledge base retrieval is deferred to Phase 2.
- **No External Tools**: No function calling, CRM lookups, or ticket creation APIs are wired in Phase 1.
- **Focus**: Ultra-low latency, robust failover, clean provider abstraction, and a responsive voice interface.
