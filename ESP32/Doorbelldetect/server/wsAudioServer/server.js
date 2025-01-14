/////////////////////////////////////////////////////////////////
/*
  Broadcasting Your Voice with ESP32-S3 & INMP441
  For More Information: https://youtu.be/qq2FRv0lCPw
  Created by Eric N. (ThatProject)
*/
/////////////////////////////////////////////////////////////////

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

const wsServer = new WebSocket.Server({ port: WS_PORT }, () =>
  console.log(`WS server is listening at ws://localhost:${WS_PORT}`)
);

// Buffer for incoming audio data
let audioBuffer = [];

// WebSocket connection handling
wsServer.on("connection", (ws, req) => {
  console.log("Connected");

  ws.on("message", (data) => {
    audioBuffer.push(data);
    packetsReceived++;
    
    // Show rate every second
    const now = Date.now();
    if (now - lastCheck >= RATE_INTERVAL) {
      const rate = (packetsReceived / (now - lastCheck)) * 1000;
      console.log(`Rate: ${rate.toFixed(1)} packets/s`);
      packetsReceived = 0;
      lastCheck = now;
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
  console.log("\nGracefully shutting down...");
  writeAudioToFile();
  process.exit();
});
