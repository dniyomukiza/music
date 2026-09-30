# GRO News pipeline

Audio news now calls Parallel Search when `PARALLEL_API_KEY` is set, then Gemini still writes scripts. Google Cloud TTS is unchanged.

Locked stack:

- **Search:** Parallel Search API (`glconnect/parallel_news_search.py`). One query per topic. Not Cursor MCP in the Flask job.
- **Scripts:** Gemini writes reporter copy from that search packet (`_gemini_reporter_scripts`).
- **Audio:** **Google Cloud TTS** (`_run_direct_tts_phase`).
- **Video:** HeyGen after a successful audio bulletin (unchanged).
- **Coordination:** Python (`_generate_broadcast_attempt`). ADK stays optional for topic categorization only.

If the key is missing or Parallel fails, Gemini uses the previous knowledge-only path so the bulletin still completes.

Production: set `PARALLEL_API_KEY` in `/etc/glconfig.json` (same pattern as HeyGen / Resend).
