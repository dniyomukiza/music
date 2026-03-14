/**
 * PCM Recorder AudioWorklet - captures mic at 16kHz, outputs Float32 for conversion to 16-bit PCM.
 * Used by music Live voice assistant (bidi-demo architecture).
 */
class PCMProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    if (inputs.length > 0 && inputs[0].length > 0) {
      const inputChannel = inputs[0][0];
      const inputCopy = new Float32Array(inputChannel);
      this.port.postMessage(inputCopy);
    }
    return true;
  }
}
registerProcessor("pcm-recorder-processor", PCMProcessor);
