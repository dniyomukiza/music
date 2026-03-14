# Music Voice Agent – Gemini Live API Setup

This guide explains how to migrate the music voice assistant from HTTP + browser TTS to **Gemini Live API** with native audio, following the [ADK bidi-demo](https://github.com/google/adk-samples/blob/main/python/agents/bidi-demo/README.md).

## Why Gemini Live?

- **Native audio output** – Natural-sounding voice (no browser SpeechSynthesis)
- **Real-time bidirectional streaming** – WebSocket, low latency
- **Audio in, audio out** – PCM 16kHz input → 24kHz output
- **Affective dialog** – Optional tone/emotion adaptation

## Architecture (from bidi-demo)

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│  WebSocket  │────────▶│ LiveRequestQueue │────────▶│  Live API   │
│   Client    │         │                  │         │   Session   │
│             │◀────────│   run_live()     │◀────────│             │
└─────────────┘         └──────────────────┘         └─────────────┘
  Upstream Task              Queue              Downstream Task
```

- **Client → Server**: Text (JSON) or raw PCM audio (16kHz, 16-bit)
- **Server → Client**: ADK `Event` objects (audio chunks, transcriptions, etc.)
- **Audio format**: PCM 16-bit little-endian (16kHz input, 24kHz output)

## Prerequisites

### 1. Upgrade google-adk

The bidi-demo uses `google-adk>=1.20.0`. Current app has `0.1.0`.

```bash
# In requirements.txt, change:
google-adk==0.1.0   →   google-adk>=1.20.0
```

**Warning**: This may affect `news_agent.py` and other ADK usage. Test after upgrade.

### 2. Environment

- `GOOGLE_API_KEY` or `GEMINI_API_KEY` (from glconfig.json or .env)
- Model: `gemini-2.5-flash-native-audio-preview-12-2025` (Gemini Live API)

### 3. Dependencies

```toml
# bidi-demo pyproject.toml
dependencies = [
  "google-adk>=1.20.0",
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
]
```

## Implementation Steps

### Step 1: Music Live Agent (ADK Agent + Tools)

Create `glconnect/music_live_agent.py`:

- **Agent** with `instruction` (same as current `SYSTEM_INSTRUCTION`)
- **Tools**: `search_songs`, `play_song`, `add_song_to_playlist`, `download_song`
- Tools must be async or sync functions with type hints and docstrings
- Tools need `user_id` and `base_url` – pass via agent state or tool context

ADK custom tools pattern:

```python
def search_songs(query: str, user_id: int | None = None, base_url: str = "") -> str:
    """Search for songs or artists in the music catalog."""
    # Use SessionLocal, models – same as music_voice_agent.search_songs_impl
    return json.dumps({"found": n, "songs": [...]})
```

### Step 2: WebSocket Endpoint (FastAPI)

Add to `glconnect/voc.py` or a new FastAPI router:

```python
@app.websocket("/ws/music/{user_id}/{session_id}")
async def music_live_websocket(websocket: WebSocket, user_id: str, session_id: str):
    await websocket.accept()
    live_request_queue = LiveRequestQueue()
    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        session_resumption=types.SessionResumptionConfig(),
    )
    # upstream_task: receive WebSocket messages → send to queue
    # downstream_task: runner.run_live() → send events to WebSocket
    await asyncio.gather(upstream_task(), downstream_task())
    live_request_queue.close()
```

### Step 3: Nginx WebSocket Proxy

Add to `nginx.conf`:

```nginx
location /ws/music/ {
    proxy_pass http://fastapi:8002;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}
```

### Step 4: Frontend – PCM Recording & Playback

From bidi-demo:

- **Recording**: `AudioContext` 16kHz → `AudioWorklet` (pcm-recorder-processor) → Float32 → Int16 PCM → send binary via WebSocket
- **Playback**: Receive base64 PCM chunks in events → decode to Int16Array → send to `pcm-player-processor` (24kHz)

Event types from ADK (see [ADK Events](https://google.github.io/adk-docs/)):

- `output_audio` – base64 PCM data
- `output_audio_transcription` – text transcript
- `input_audio_transcription` – user speech transcript
- `tool_call`, `tool_result` – tool execution

### Step 5: Tool Context (user_id, base_url)

The tools need the current user and base URL. Options:

1. **WebSocket URL**: `/ws/music/{user_id}/{session_id}` – pass `user_id` from session
2. **First message**: Client sends `{"type": "config", "user_id": 123, "base_url": "https://glc.cool"}` before audio
3. **Session storage**: Store in `InMemorySessionService` per session

## File Structure (Reference)

```
glconnect/
├── music_live_agent.py      # ADK Agent + music tools
├── music_voice_agent.py    # (keep for HTTP fallback)
└── voc.py                  # Add WebSocket route

glconnect/static/
├── pcm-recorder-processor.js
├── pcm-player-processor.js
└── music-live-client.js     # WebSocket + audio logic

templates/book_platform/
└── music_dashboard.html     # Use Live client when available
```

## Testing

1. Run FastAPI: `uvicorn glconnect.voc:app --host 0.0.0.0 --port 8002`
2. Open music dashboard, click Voice Assistant
3. Connect WebSocket, send text or start microphone
4. Verify audio responses and tool actions (play, add to playlist, etc.)

## Fallback

If Gemini Live is unavailable (e.g. model not found, quota), keep the current HTTP + browser SpeechSynthesis flow as fallback.

## References

- [ADK Gemini Live bidi-demo](https://github.com/google/adk-samples/blob/main/python/agents/bidi-demo/README.md)
- [Gemini Live API](https://ai.google.dev/gemini-api/docs/live)
- [ADK Custom Tools](https://google.github.io/adk-docs/tools-custom/function-tools/)
