"""
Music Live WebSocket - Gemini Live API (bidi-demo architecture).
Adds WebSocket endpoint to FastAPI app.
"""

import asyncio
import base64
import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

# Lazy imports to avoid loading ADK at module level (can fail if deps missing)
def _get_runner():
    from google.adk.agents.live_request_queue import LiveRequestQueue
    from google.adk.agents.run_config import RunConfig, StreamingMode
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from glconnect.music_live_agent import music_agent, set_music_live_context

    session_service = InMemorySessionService()
    runner = Runner(app_name="music-live", agent=music_agent, session_service=session_service)
    return runner, session_service, types, LiveRequestQueue, RunConfig, StreamingMode, set_music_live_context


async def handle_music_live_websocket(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
    base_url: Optional[str] = None,
) -> None:
    """Handle WebSocket connection for music Live API."""
    try:
        runner, session_service, types, LiveRequestQueue, RunConfig, StreamingMode, set_music_live_context = _get_runner()
    except Exception as e:
        logger.error(f"Failed to load music Live ADK: {e}")
        await websocket.close(code=1011, reason=str(e))
        return

    import os
    base_url = base_url or os.getenv("FRONTEND_BASE_URL", "https://glc.cool")
    try:
        uid = int(user_id) if user_id and user_id.isdigit() else None
    except ValueError:
        uid = None
    set_music_live_context(uid, base_url)

    await websocket.accept()
    logger.debug(f"Music Live WebSocket accepted: user_id={user_id}, session_id={session_id}")

    agent = getattr(runner, "agent", None)
    model_name = getattr(agent, "model", "") if agent else ""
    is_native_audio = "native-audio" in str(model_name).lower()

    if is_native_audio:
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(),
        )
    else:
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["TEXT"],
            input_audio_transcription=None,
            output_audio_transcription=None,
            session_resumption=types.SessionResumptionConfig(),
        )

    session = await session_service.get_session(app_name="music-live", user_id=user_id, session_id=session_id)
    if not session:
        await session_service.create_session(app_name="music-live", user_id=user_id, session_id=session_id)

    live_request_queue = LiveRequestQueue()

    async def upstream_task():
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

    def _extract_actions_from_event(event):
        """Extract play/add_to_playlist/download/show_transcript actions from tool results for client execution."""
        actions = []
        try:
            for fr in (event.get_function_responses() or []):
                resp = getattr(fr, "response", None)
                if isinstance(resp, dict):
                    if "action" in resp:
                        actions.append(resp["action"])
                    elif "result" in resp:
                        r = resp["result"]
                        if isinstance(r, dict) and "action" in r:
                            actions.append(r["action"])
                        elif isinstance(r, str):
                            try:
                                data = json.loads(r)
                                if isinstance(data, dict) and "action" in data:
                                    actions.append(data["action"])
                            except json.JSONDecodeError:
                                pass
                elif isinstance(resp, str):
                    try:
                        data = json.loads(resp)
                        if isinstance(data, dict) and "action" in data:
                            actions.append(data["action"])
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        return actions

    async def downstream_task():
        async for event in runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            for action in _extract_actions_from_event(event):
                logger.info("Sending music_action to client: %s", action.get("type"))
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
