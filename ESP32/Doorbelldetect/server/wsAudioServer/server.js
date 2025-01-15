const path = require("path");
const express = require("express");
const WebSocket = require("ws");
const fs = require("fs");
const app = express();

const WS_PORT = process.env.WS_PORT || 3003;

// Add rate tracking
let packetsReceived = 0;
let lastCheck = Date.now();
const RATE_INTERVAL = 1000; // 1 second

const WRITE_INTERVAL = 5 * 60 * 1000; // 5 minutes
let lastWrite = Date.now();
let totalBytes = 0;
let outputFile;

const wsServer = new WebSocket.Server({ port: WS_PORT }, () =>
  console.log(`WS server is listening at ws://localhost:${WS_PORT}`)
);

// Double buffer system
let audioBuffers = {
  current: [],
  writing: []
};
let isWriting = false;

// WebSocket connection handling
wsServer.on("connection", (ws, req) => {
  console.log("Connected");
  if (!outputFile) initWavFile();

  ws.on("message", (data) => {
    audioBuffers.current.push(data);
    packetsReceived++;
    
    // Show rate every second
    const now = Date.now();
    if (now - lastCheck >= RATE_INTERVAL) {
      const rate = (packetsReceived / (now - lastCheck)) * 1000;
      console.log(`Rate: ${rate.toFixed(1)} packets/s`);
      packetsReceived = 0;
      lastCheck = now;
    }

    if (now - lastWrite >= WRITE_INTERVAL) {
      appendAudioData();
      lastWrite = now;
    }
  });

  ws.on("close", () => {
    console.log("Client disconnected");
  });
});

// Generate WAV header
function createWavHeader(audioLength) {
  const header = Buffer.alloc(44);
  const fileSize = audioLength + 44 - 8;

  header.write('RIFF', 0); // ChunkID
  header.writeUInt32LE(fileSize, 4); // ChunkSize
  header.write('WAVE', 8); // Format
  header.write('fmt ', 12); // Subchunk1ID
  header.writeUInt32LE(16, 16); // Subchunk1Size (16 for PCM)
  header.writeUInt16LE(1, 20); // AudioFormat (1 for PCM)
  header.writeUInt16LE(1, 22); // NumChannels (1 for mono)
  header.writeUInt32LE(44100, 24); // SampleRate
  header.writeUInt32LE(44100 * 2, 28); // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
  header.writeUInt16LE(2, 32); // BlockAlign (NumChannels * BitsPerSample/8)
  header.writeUInt16LE(16, 34); // BitsPerSample
  header.write('data', 36); // Subchunk2ID
  header.writeUInt32LE(audioLength, 40); // Subchunk2Size (NumSamples * NumChannels * BitsPerSample/8)

  return header;
}

function initWavFile() {
  const header = createWavHeader(0);  // Initial header with 0 length
  outputFile = fs.createWriteStream('audio_recording.wav');
  outputFile.write(header);
}

function appendAudioData() {
  if (isWriting || audioBuffers.current.length === 0) return;
  
  isWriting = true;
  // Swap buffers
  [audioBuffers.current, audioBuffers.writing] = [[], audioBuffers.current];
  
  const audioData = Buffer.concat(audioBuffers.writing);
  outputFile.write(audioData, (err) => {
    if (err) console.error('Write error:', err);
    totalBytes += audioData.length;
    console.log(`Appended ${audioData.length} bytes, total: ${totalBytes}`);
    audioBuffers.writing = [];
    isWriting = false;
  });
}

function finalizeWavFile() {
  if (outputFile) {
    outputFile.end();
    // Update WAV header with final size
    const fd = fs.openSync('audio_recording.wav', 'r+');
    const header = createWavHeader(totalBytes);
    fs.writeSync(fd, header, 0, 44, 0);
    fs.closeSync(fd);
  }
}

// Write audio buffer to file on exit
function writeAudioToFile() {
  const filename = "audio_recording.wav";
  const audioData = Buffer.concat(audioBuffer);
  const wavHeader = createWavHeader(audioData.length);

  // Write WAV header and audio data to file
  fs.writeFileSync(filename, wavHeader);
  fs.appendFileSync(filename, audioData);
  console.log(`\nSaved to ${filename}`);
}

// Handle process exit
process.on("SIGINT", () => {
  console.log("\nFinalizing recording...");
  appendAudioData();
  finalizeWavFile();
  process.exit();
});
