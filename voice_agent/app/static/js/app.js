/**
 * Book Platform Voice Agent - Audio-only (voice in, voice out)
 * Works on desktop and mobile. Tap Start Audio to speak.
 */

import { initAudioPlayer, playPcmFromBase64, endOfAudio } from "./audio-player.js";

const userId = "user-1";
const sessionId = "session-" + Math.random().toString(36).substring(7);
let websocket = null;
let isRecording = false;
let mediaRecorder = null;
let audioContext = null;

const statusIndicator = document.getElementById("statusIndicator");
const statusText = document.getElementById("statusText");
const audioBtn = document.getElementById("audioBtn");

let audioPlayerReady = false;

function getWebSocketUrl() {
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const base = location.pathname.startsWith("/voice-agent") ? "/voice-agent" : "";
  const wsPath = base ? `${base}/ws` : "/ws";
  return `${wsProtocol}//${location.host}${wsPath}/${userId}/${sessionId}`;
}

function setStatus(connected) {
  statusIndicator.className = "status " + (connected ? "connected" : "disconnected");
  statusText.textContent = connected ? "Connected" : "Disconnected";
}

function connectWebSocket() {
  if (websocket && websocket.readyState === WebSocket.OPEN) return;
  websocket = new WebSocket(getWebSocketUrl());

  websocket.onopen = async () => {
    setStatus(true);
    if (!audioPlayerReady) {
      await initAudioPlayer(24000);
      audioPlayerReady = true;
    }
  };

  websocket.onclose = () => {
    setStatus(false);
  };

  websocket.onerror = (err) => {
    console.error("WebSocket error:", err);
    setStatus(false);
  };

  websocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleEvent(data);
    } catch (e) {
      console.warn("Could not parse event:", e);
    }
  };
}

function handleEvent(event) {
  // Play PCM audio chunks (agent voice) - no text display
  if (event.content?.parts) {
    for (const part of event.content.parts) {
      const blob = part.inlineData || part.inline_data;
      if (blob?.data && (blob.mimeType || blob.mime_type || "").startsWith("audio/pcm") && audioPlayerReady) {
        playPcmFromBase64(blob.data, blob.mimeType || blob.mime_type);
      }
    }
  }

  if (event.interrupted && audioPlayerReady) {
    endOfAudio();
  }
}

function sendAudioChunk(audioData) {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send(audioData);
  }
}

async function startAudio() {
  if (isRecording) {
    stopRecording();
    return;
  }

  // Connect and init on user gesture (required for mobile/iOS)
  connectWebSocket();
  if (!audioPlayerReady) {
    await initAudioPlayer(24000);
    audioPlayerReady = true;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000,
    });

    const source = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(4096, 1, 1);

    processor.onaudioprocess = (e) => {
      if (!isRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      const pcm16 = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      sendAudioChunk(pcm16.buffer);
    };

    source.connect(processor);
    processor.connect(audioContext.destination);

    mediaRecorder = { stream, processor, source };
    isRecording = true;
    audioBtn.textContent = "Stop Audio";
    audioBtn.classList.add("recording");
  } catch (err) {
    console.error("Microphone access error:", err);
    const toast = document.getElementById("errorToast");
    if (toast) {
      toast.textContent = "Could not access microphone. Please allow microphone access.";
      setTimeout(() => { toast.textContent = ""; }, 5000);
    }
  }
}

function stopRecording() {
  isRecording = false;
  audioBtn.textContent = "Start Audio";
  audioBtn.classList.remove("recording");
  if (mediaRecorder) {
    mediaRecorder.source.disconnect();
    mediaRecorder.processor.disconnect();
    mediaRecorder.stream.getTracks().forEach((t) => t.stop());
    mediaRecorder = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
}

audioBtn.addEventListener("click", () => {
  startAudio();
});
