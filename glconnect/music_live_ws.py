"""
Music Live WebSocket - Gemini Live API (bidi-demo architecture).
Adds WebSocket endpoint to FastAPI app.
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Module-level cache for ADK components
_cached_adk = None

# Lazy imports to avoid loading ADK at module level (can fail if deps missing)
def _get_runner():
    global _cached_adk
    if _cached_adk:
        return _cached_adk

    from google.adk.agents.live_request_queue import LiveRequestQueue
    from google.adk.agents.run_config import RunConfig, StreamingMode, ToolThreadPoolConfig
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from glconnect.music_live_agent import music_agent, set_music_live_context

    session_service = InMemorySessionService()
    runner = Runner(app_name="music-live", agent=music_agent, session_service=session_service)
    
    _cached_adk = (runner, session_service, types, LiveRequestQueue, RunConfig, StreamingMode, set_music_live_context, ToolThreadPoolConfig)
    return _cached_adk


async def handle_music_live_websocket(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
    base_url: Optional[str] = None,
) -> None:
    """Handle WebSocket connection for music Live API."""
    try:
        uid = int(user_id) if user_id and user_id.isdigit() else None
    except ValueError:
        uid = None

    if uid is None:
        await websocket.accept()
        await websocket.close(code=1008, reason="Invalid music session user")
        return
    if uid != 0:
        from glconnect.music_live_auth import validate_music_live_ws_token

        token = websocket.query_params.get("token")
        if not validate_music_live_ws_token(token, uid):
            await websocket.accept()
            await websocket.close(code=1008, reason="Unauthorized music session")
            return

    try:
        runner, session_service, types, LiveRequestQueue, RunConfig, StreamingMode, set_music_live_context, ToolThreadPoolConfig = _get_runner()
    except Exception as e:
        logger.error(f"Failed to load music Live ADK: {e}")
        await websocket.accept()
        await websocket.close(code=1011, reason=str(e))
        return

    import os
    base_url = base_url or os.getenv("FRONTEND_BASE_URL", "https://ndotonic.com")
    set_music_live_context(uid if uid != 0 else None, base_url)

    await websocket.accept()
    logger.debug(f"Music Live WebSocket accepted: user_id={user_id}, session_id={session_id}")

    agent = getattr(runner, "agent", None)
    model_name = getattr(agent, "model", "") if agent else ""
    is_native_audio = "native-audio" in str(model_name).lower()

    # Session resumption is only supported on Vertex AI backend; must be None for Google AI (Gemini API)
    if is_native_audio:
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["AUDIO"],
            input_audio_transcription=None,
            output_audio_transcription=None,
            session_resumption=None,
            tool_thread_pool_config=ToolThreadPoolConfig(max_workers=4),
            enable_affective_dialog=False,
        )
    else:
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["TEXT"],
            input_audio_transcription=None,
            output_audio_transcription=None,
            session_resumption=None,
            tool_thread_pool_config=ToolThreadPoolConfig(max_workers=4),
        )

    session = await session_service.get_session(app_name="music-live", user_id=user_id, session_id=session_id)
    if not session:
        await session_service.create_session(app_name="music-live", user_id=user_id, session_id=session_id)

    live_request_queue = LiveRequestQueue()

    async def upstream_task():
        try:
            while True:
                message = await websocket.receive()
                if "bytes" in message:
                    audio_data = message["bytes"]
                    audio_blob = types.Blob(mime_type="audio/pcm;rate=16000", data=audio_data)
                    live_request_queue.send_realtime(audio_blob)
                elif "text" in message:
                    try:
                        json_message = json.loads(message["text"])
                        if json_message.get("type") == "text":
                            content = types.Content(parts=[types.Part(text=json_message["text"])])
                            live_request_queue.send_content(content)
                        elif json_message.get("type") == "config":
                            base = json_message.get("base_url")
                            if base:
                                set_music_live_context(uid, base)
                    except json.JSONDecodeError:
                        pass
        except WebSocketDisconnect:
            pass

    def _extract_actions_from_event(event):
        """Extract play/add_to_playlist/download/show_transcript actions from tool results for client execution."""
        actions = []
        try:
            # 1. Check function_responses directly (most common for tools)
            fr_list = event.get_function_responses() or []
            for fr in fr_list:
                resp = getattr(fr, "response", None)
                if not resp: continue
                
                # Tools return JSON strings or dicts
                data = None
                if isinstance(resp, dict):
                    data = resp
                elif isinstance(resp, str):
                    try: data = json.loads(resp)
                    except: pass
                
                if data and isinstance(data, dict):
                    # Standard format: {"action": {...}}
                    if "action" in data:
                        actions.append(data["action"])
                    # Fallback for nested results: {"result": {"action": {...}}}
                    elif "result" in data and isinstance(data["result"], dict) and "action" in data["result"]:
                        actions.append(data["result"]["action"])

            # 2. Fast fallback for content parts if needed (less likely with get_function_responses)
            if not actions and hasattr(event, "content") and event.content:
                parts = getattr(event.content, "parts", None) or []
                for p in parts:
                    fr = getattr(p, "function_response", None)
                    if not fr: continue
                    resp = getattr(fr, "response", None)
                    if isinstance(resp, dict) and "action" in resp:
                        actions.append(resp["action"])
                    elif isinstance(resp, str):
                        try:
                            d = json.loads(resp)
                            if isinstance(d, dict) and "action" in d:
                                actions.append(d["action"])
                        except: pass

        except Exception as e:
            logger.debug("_extract_actions_from_event error: %s", e)
        return actions

    async def downstream_task():
        async for event in runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            actions = _extract_actions_from_event(event)
            if actions:
                for action in actions:
                    logger.info("Sending music_action to client: %s (song_id=%s, download_id=%s)", action.get("type"), action.get("song_id"), action.get("download_id"))
                    await websocket.send_text(json.dumps({"type": "music_action", "action": action}))
            event_json = event.model_dump_json(exclude_none=True, by_alias=True)
            await websocket.send_text(event_json)

    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except WebSocketDisconnect:
        logger.debug("Music Live WebSocket disconnected")
    except Exception as e:
        logger.error(f"Music Live WebSocket error: {e}", exc_info=True)
    finally:
        live_request_queue.close()
