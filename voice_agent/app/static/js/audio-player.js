/**
 * PCM audio player for Gemini Live API output.
 * Receives 16-bit PCM at 24kHz or 16kHz and plays through Web Audio API.
 */
let audioContext = null;
let sampleRate = 24000; // Default; parse from mimeType if present
let nextStartTime = 0;

function base64ToArrayBuffer(base64) {
  const binary = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

export async function initAudioPlayer(rate = 24000) {
  sampleRate = rate;
  if (audioContext) return audioContext;
  audioContext = new (window.AudioContext || window.webkitAudioContext)({
    sampleRate: sampleRate,
  });
  return audioContext;
}

export function playPcmChunk(arrayBuffer, rate) {
  if (!audioContext) return;
  const sr = rate || sampleRate;
  const int16 = new Int16Array(arrayBuffer);
  const float32 = new Float32Array(int16.length);
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768;
  }
  const buffer = audioContext.createBuffer(1, float32.length, sr);
  buffer.getChannelData(0).set(float32);
  const source = audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(audioContext.destination);
  const startTime = Math.max(audioContext.currentTime, nextStartTime);
  source.start(startTime);
  nextStartTime = startTime + buffer.duration;
}

export function playPcmFromBase64(base64, mimeType) {
  const buf = base64ToArrayBuffer(base64);
  const m = (mimeType || "").match(/rate=(\d+)/);
  const rate = m ? parseInt(m[1], 10) : 24000;
  playPcmChunk(buf, rate);
}

export function endOfAudio() {
  nextStartTime = 0;
}
