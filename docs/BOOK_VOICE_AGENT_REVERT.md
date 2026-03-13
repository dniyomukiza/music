# Book Platform Voice Agent - Revert Instructions

If the voice agent causes issues in production, follow these steps to disable or fully revert it.

## Docker Compose Deployment

The voice agent runs as a separate container with its own ADK version (1.20+):
- **Service**: `voice_agent` in docker-compose.yml
- **URL**: https://glc.cool/voice-agent/ (proxied via nginx)
- **WebSocket**: wss://glc.cool/voice-agent/ws/...
- **Env**: `ENABLE_BOOK_VOICE_AGENT`, `VOICE_AGENT_URL`

## Quick Disable (No Code Changes)

Set the environment variable to turn off the feature:

```bash
export ENABLE_BOOK_VOICE_AGENT=false
```

Or in `.env`:
```
ENABLE_BOOK_VOICE_AGENT=false
```

Restart the Flask app. The "Voice Assistant" button will no longer appear in the marketplace.

## Full Revert (Remove Integration)

If you need to remove the integration from the main app:

### 1. Remove marketplace template changes

In `glconnect/templates/book_platform/marketplace.html`, remove the voice agent button block:

```html
{% if enable_voice_agent %}
<a href="{{ voice_agent_url }}" target="_blank" rel="noopener"
   class="btn btn-lg btn-info">
    <i class="fas fa-microphone me-2"></i>Voice Assistant
</a>
{% endif %}
```

### 2. Remove route changes

In `glconnect/book_platform_routes.py`, in the `marketplace()` function:

- Remove the `enable_voice_agent` and `voice_agent_url` variable assignments
- Remove these from both `render_template()` calls (success and exception paths):
  - `enable_voice_agent=enable_voice_agent`
  - `voice_agent_url=voice_agent_url`

### 3. Delete voice agent folder (optional)

```bash
rm -rf voice_agent/
```

### 4. Remove .gitignore entry (optional)

If you deleted the voice_agent folder and want to remove the ignore rule from `.gitignore`:

Remove the line:
```
voice_agent/
```

## What Was Added

| Location | Change |
|----------|--------|
| `glconnect/book_platform_routes.py` | `enable_voice_agent`, `voice_agent_url` passed to marketplace template |
| `glconnect/templates/book_platform/marketplace.html` | Conditional "Voice Assistant" button |
| `voice_agent/` | New self-contained folder (FastAPI app, tools, static UI) |
| `.gitignore` | `voice_agent/` entry |
| Environment | `ENABLE_BOOK_VOICE_AGENT`, `VOICE_AGENT_URL` (optional) |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_BOOK_VOICE_AGENT` | `false` | Set to `true` to show the Voice Assistant button |
| `VOICE_AGENT_URL` | `http://localhost:8001` | URL where the voice agent runs |
