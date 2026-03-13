"""
FastAPI application for the book platform voice agent.
WebSocket at /ws/{user_id}/{session_id} for bidirectional streaming.
"""

import asyncio
import base64
import json
import os
import logging
import warnings
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Load .env from voice_agent root and project root
for p in [
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if p.exists():
        load_dotenv(p)
        break

# Fallback: load from glconfig.json (production mount at /etc/glconfig.json, same as main app)
for cfg_path in [Path("/etc/glconfig.json"), Path("glconfig.json"), Path(__file__).parent.parent.parent / "glconfig.json"]:
    if cfg_path.exists() and cfg_path.stat().st_size > 0:
        try:
            cfg = json.loads(cfg_path.read_text())
            if cfg.get("GOOGLE_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
                os.environ["GOOGLE_API_KEY"] = cfg["GOOGLE_API_KEY"]
            if cfg.get("GEMINI_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
                os.environ["GEMINI_API_KEY"] = cfg["GEMINI_API_KEY"]
            break
        except Exception:
            pass

# Import agent after loading environment variables
from app.book_agent.agent import agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

APP_NAME = "book-voice-agent"

app = FastAPI(title="Book Platform Voice Agent")

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=agent, session_service=session_service)


@app.get("/")
async def root():
    """Serve the index.html page."""
    return FileResponse(static_dir / "index.html")


@app.websocket("/ws/{user_id}/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    session_id: str,
    proactivity: bool = False,
    affective_dialog: bool = False,
) -> None:
    """WebSocket endpoint for bidirectional streaming with ADK."""
    logger.info(
        f"WebSocket connection: user_id={user_id}, session_id={session_id}"
    )
    await websocket.accept()

    model_name = agent.model or ""
    is_native_audio = "native-audio" in model_name.lower()
    logger.info("Model: %s, audio_mode=%s", model_name, is_native_audio)

    if is_native_audio:
        response_modalities = ["AUDIO"]
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=response_modalities,
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(),
            proactivity=(
                types.ProactivityConfig(proactive_audio=True)
                if proactivity
                else None
            ),
            enable_affective_dialog=affective_dialog if affective_dialog else None,
        )
    else:
        response_modalities = ["TEXT"]
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=response_modalities,
            input_audio_transcription=None,
            output_audio_transcription=None,
            session_resumption=types.SessionResumptionConfig(),
        )

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if not session:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    live_request_queue = LiveRequestQueue()

    async def upstream_task() -> None:
        """Receive messages from WebSocket and send to LiveRequestQueue."""
        while True:
            message = await websocket.receive()

            if "bytes" in message:
                audio_data = message["bytes"]
                audio_blob = types.Blob(
                    mime_type="audio/pcm;rate=16000", data=audio_data
                )
                live_request_queue.send_realtime(audio_blob)

            elif "text" in message:
                json_message = json.loads(message["text"])

                if json_message.get("type") == "text":
                    content = types.Content(
                        parts=[types.Part(text=json_message["text"])]
                    )
                    live_request_queue.send_content(content)

                elif json_message.get("type") == "image":
                    image_data = base64.b64decode(json_message["data"])
                    mime_type = json_message.get("mimeType", "image/jpeg")
                    image_blob = types.Blob(
                        mime_type=mime_type, data=image_data
                    )
                    live_request_queue.send_realtime(image_blob)

    async def downstream_task() -> None:
        """Receive events from run_live() and send to WebSocket."""
        async for event in runner.run_live(
            user_id=user_id,
            session_id=session_id,
            live_request_queue=live_request_queue,
            run_config=run_config,
        ):
            event_json = event.model_dump_json(
                exclude_none=True, by_alias=True
            )
            await websocket.send_text(event_json)

    try:
        await asyncio.gather(upstream_task(), downstream_task())
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error in streaming: {e}", exc_info=True)
    finally:
        live_request_queue.close()
