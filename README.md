# Real-Time Technical Support Voice Agent (Phase 1)

A high-performance, real-time voice technical support agent built using **LiveKit Agents (Python)**, **Deepgram streaming STT**, **Google Gemini Flash (temp 0.3)** with automatic **Groq fallback (temp 0.3)**, and **Fish Audio streaming TTS** (swappable in one line). The web interface is built with **Next.js 14** and **livekit-client**, featuring a modern dark-mode aesthetic with real-time **Listening / Thinking / Speaking** state indicators.

---

## 1. Project Structure

```
├── agent/
│   ├── .venv/                 # Python virtual environment (ignored/local)
│   ├── main.py                # LiveKit voice agent worker & support persona
│   ├── stt.py                 # Deepgram Streaming STT configuration module
│   ├── llm.py                 # Gemini Flash + Groq fallback provider abstraction
│   ├── tts.py                 # Fish Audio streaming TTS configuration module
│   └── requirements.txt       # Pinned dependencies
├── web/
│   ├── src/
│   │   └── app/
│   │       ├── api/token/
│   │       │   └── route.ts   # Next.js Route Handler for minting LiveKit tokens
│   │       ├── globals.css    # Premium glassmorphic styling & audio visualizer animations
│   │       ├── layout.tsx     # Application HTML shell and metadata
│   │       └── page.tsx       # UI with Connect button, mic toggle, and state visualizer
│   ├── package.json           # Pinned npm dependencies
│   ├── tsconfig.json          # TypeScript compiler configuration
│   └── next.config.js         # Next.js runtime configuration
├── knowledge/
│   └── README.md              # Placeholder for Phase 2 RAG & technical documents
├── docs/
│   └── DECISIONS.md           # Architecture, provider failover, and persona decisions
├── .env.example               # Template environment variables
└── README.md                  # Project documentation & run guide
```

---

## 2. Prerequisites

- **Python 3.10+** (Tested on Python 3.11.7)
- **Node.js 18+** (Tested on Node v22.20.0, npm 10.9.3)
- **LiveKit Server / Cloud Project**:
  - `LIVEKIT_URL` (e.g. `wss://<your-subdomain>.livekit.cloud`)
  - `LIVEKIT_API_KEY`
  - `LIVEKIT_API_SECRET`
- **Provider API Keys**:
  - `DEEPGRAM_API_KEY` ([console.deepgram.com](https://console.deepgram.com))
  - `GOOGLE_API_KEY` ([aistudio.google.com](https://aistudio.google.com))
  - `GROQ_API_KEY` ([console.groq.com](https://console.groq.com))
  - `FISH_API_KEY` ([fish.audio](https://fish.audio))

---

## 3. Environment Configuration

1. Copy `.env.example` to `.env` in the project root:
   ```bash
   cp .env.example .env
   ```
2. Populate the keys with your credentials:
   ```env
   # LiveKit Credentials
   LIVEKIT_URL=wss://your-project.livekit.cloud
   LIVEKIT_API_KEY=devkey
   LIVEKIT_API_SECRET=secret
   NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud

   # Speech-to-Text
   DEEPGRAM_API_KEY=your_deepgram_api_key

   # Large Language Model (Primary: Gemini Flash, Fallback: Groq)
   GOOGLE_API_KEY=your_gemini_api_key
   GROQ_API_KEY=your_groq_api_key

   # Text-to-Speech
   FISH_API_KEY=your_fish_audio_api_key
   ```

*(Note: `agent/main.py` automatically detects and loads the `.env` file from the project root or the `agent/` folder).*

---

## 4. How to Run

### Step 1: Start the Python Voice Agent Worker

Open a terminal and navigate to `agent/`:

```bash
cd agent

# 1. Create a virtual environment (if not already created)
python -m venv .venv

# 2. Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# macOS / Linux:
source .venv/bin/activate

# 3. Install pinned dependencies
pip install -r requirements.txt

# 4. Start the agent worker in development mode
python main.py dev
```

*The worker process will connect to your LiveKit room dispatcher and wait for incoming calls.*

---

### Step 2: Start the Next.js Web Client

In a second terminal, navigate to `web/`:

```bash
cd web

# 1. Install dependencies
npm install

# 2. Start the development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

### Step 3: Test the Real-Time Support Agent

1. Click **"Start Voice Support"**.
2. Allow microphone access when prompted by the browser.
3. The visual indicator will transition:
   - **Connecting**: Minting JWT token and joining the WebRTC room.
   - **Listening** *(cyan aura)*: Agent is actively listening to your microphone.
   - **Thinking** *(violet aura)*: When you stop speaking, the agent queries Gemini Flash (or Groq if Gemini fails).
   - **Speaking** *(emerald green aura & sound waves)*: The agent speaks its synthesized reply via Fish Audio.
4. Use the **Microphone** button to mute or unmute yourself at any time.
5. Click **"End Call"** to hang up.

---

## 5. Swapping Providers in One Line

Every provider is isolated in its own configuration module under `agent/`:

### 1. Swapping STT (`agent/stt.py`)
To change the STT provider or model, edit the return statement in [`agent/stt.py`](file:///d:/Technical-assitant%20agent/agent/stt.py):
```python
# To switch to Google STT or OpenAI Whisper:
return google.STT(languages=["en-US"])
# or
return openai.STT()
```

### 2. Swapping LLM (`agent/llm.py`)
To bypass the fallback adapter or switch models, edit `get_llm()` in [`agent/llm.py`](file:///d:/Technical-assitant%20agent/agent/llm.py):
```python
# Direct single provider:
return get_gemini_llm()
# or
return get_groq_llm()
# or
return openai.LLM(model="gpt-4o-mini")
```

### 3. Swapping TTS (`agent/tts.py`)
To change the TTS provider, edit `get_tts()` in [`agent/tts.py`](file:///d:/Technical-assitant%20agent/agent/tts.py):
```python
# To switch to Deepgram Aura or Cartesia:
return deepgram.TTS(model="aura-asteria-en")
# or
return cartesia.TTS(model="sonic-3")
# or
return openai.TTS(voice="alloy")
```

---

## 6. Pinned Dependency Versions

### Agent (`agent/requirements.txt`)
- `livekit-agents==1.8.8`
- `livekit-plugins-deepgram==1.8.8`
- `livekit-plugins-google==1.8.8`
- `livekit-plugins-groq==1.8.8`
- `livekit-plugins-fishaudio==1.8.8`
- `livekit-plugins-silero==1.8.8`
- `python-dotenv==1.2.4`

### Web Client (`web/package.json`)
- `next`: `14.2.25`
- `react`: `18.3.1`
- `react-dom`: `18.3.1`
- `livekit-client`: `2.23.0`
- `livekit-server-sdk`: `2.19.1`
- `typescript`: `5.7.3`

---

## 7. Scope Boundaries in Phase 1

- **English only**.
- **Max 2 sentences per spoken reply** enforced strictly in the agent system instructions.
- **Deterministic support persona** configured with `temperature: 0.3`.
- **No RAG or external tools** included in Phase 1 (reserved for Phase 2).
