/**
 * PCM Recorder AudioWorklet - captures mic at 16kHz, outputs Float32 for conversion to 16-bit PCM.
 * Used by music Live voice assistant (bidi-demo architecture).
 */
class PCMProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    if (inputs[0]?.[0]) this.port.postMessage(inputs[0][0].slice(0));
    return true;
  }
}
registerProcessor("pcm-recorder-processor", PCMProcessor);
