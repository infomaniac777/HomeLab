import asyncio
import websockets
import wave
from datetime import datetime
import numpy as np
import io
from audio_AI import classify_wav
import struct
import requests
import logging
import os

# Configure single logger instance
logger = logging.getLogger('doorbell_detector')
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent propagation to root logger

# Add formatter to logger
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Configuration
WS_PORT = 3003
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2
BUFFER_DURATION = 6  # seconds
BUFFER_SIZE_CLASSIFY = SAMPLE_RATE * SAMPLE_WIDTH *  CHANNELS * BUFFER_DURATION
RECORD_AUDIO = False
CONFIDENCE_THRESHOLD = 0.7

# Add these variables after existing configuration
PACKET_STATS_INTERVAL = 60  # Print stats every second
packet_count = 0
bytes_received = 0
last_stats_time = datetime.now()

# Add after existing global variables
audio_buffer = io.BytesIO()

# Add constants for header positions
RIFF_SIZE_OFFSET = 4
DATA_SIZE_OFFSET = 40

# State variables
packets_received = 0
last_check = datetime.now()
output_file = None
total_disconnected = 0

logger.info("Initial configuration complete.")

# Add new globals

API_ENDPOINT = "http://192.168.0.7:3004/message"
API_TIMEOUT = 3  # seconds

API_PARAMS = {
    "token": "CHANGE_ME_GOTIFY_TOKEN",
    "title": "Doorbell",
    "message": "Doorbell detected",
    "priority": 9,
}


def send_detection(class_name, confidence):
    try:
        API_PARAMS['message'] = f"{class_name} detected with confidence {confidence:.2%}" 
        response = requests.post(
            API_ENDPOINT,
            params=API_PARAMS,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        logger.info(f"Detection sent: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send detection: {e}")


def create_wav_header(sample_rate=16000, channels=1, sample_width=2):
    # RIFF chunk descriptor
    header = b'RIFF'
    header += b'\x00\x00\x00\x00'  # placeholder for file size
    header += b'WAVE'
    
    # fmt sub-chunk
    header += b'fmt '
    header += struct.pack('<I', 16)  # fmt chunk size
    header += struct.pack('<H', 1)   # audio format (PCM)
    header += struct.pack('<H', channels)
    header += struct.pack('<I', sample_rate)
    header += struct.pack('<I', sample_rate * channels * sample_width)  # byte rate
    header += struct.pack('<H', channels * sample_width)  # block align
    header += struct.pack('<H', sample_width * 8)  # bits per sample
    
    # data sub-chunk
    header += b'data'
    header += b'\x00\x00\x00\x00'  # placeholder for data size
    
    return header

async def audio_server(websocket):
    global last_check, total_disconnected
    global packet_count, bytes_received, last_stats_time
    
    # Initialize buffer
    audio_buffer = io.BytesIO()
    audio_buffer.write(create_wav_header(SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH))
    data_size = 0
    
    try:
        async for message in websocket:
            # Update packet statistics
            packet_count += 1
            bytes_received += len(message)
            
            # Write audio data and track size
            data_size += len(message)
            audio_buffer.write(message)
            
            # Print statistics every PACKET_STATS_INTERVAL seconds
            now = datetime.now()
            if (now - last_stats_time).total_seconds() >= PACKET_STATS_INTERVAL:
                elapsed = (now - last_stats_time).total_seconds()
                pps = packet_count / elapsed
                bps = bytes_received / elapsed
                logger.info(f"Packet Rate: {pps:.2f} p/s, Data Rate: {(bps * 8)/1024:.2f} Kbps")
                packet_count = 0
                bytes_received = 0
                last_stats_time = now

            if data_size >= BUFFER_SIZE_CLASSIFY:
                # Update WAV header
                audio_buffer.seek(RIFF_SIZE_OFFSET)
                audio_buffer.write(struct.pack('<I', data_size + 36))
                audio_buffer.seek(DATA_SIZE_OFFSET)
                audio_buffer.write(struct.pack('<I', data_size))
                
                # Classify directly
                audio_buffer.seek(0)
                class_name, confidence = classify_wav(audio_buffer)
                logger.info(f"Predicted: {class_name} ({confidence:.2%})")
                if class_name == 'Music' and confidence > CONFIDENCE_THRESHOLD:
                    send_detection(class_name, confidence)
                
                # Reset buffer
                audio_buffer = io.BytesIO()
                audio_buffer.write(create_wav_header(SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH))
                data_size = 0
                
    except websockets.exceptions.ConnectionClosed:
        total_disconnected += 1
        logger.warning(f"Client disconnected, total: {total_disconnected}")

def init_wav_file():
    global output_file
    output_file = wave.open("audio_recording.wav", "wb")
    output_file.setnchannels(CHANNELS)
    output_file.setsampwidth(SAMPLE_WIDTH)
    output_file.setframerate(SAMPLE_RATE)

async def main():
    global template_spectrum
    if RECORD_AUDIO:
        init_wav_file()
    # template_spectrum = load_template_spectrum()
    async with websockets.serve(audio_server, "0.0.0.0", WS_PORT):
        logger.info(f"WebSocket server listening on port {WS_PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    logger.info("Starting main ...")
    packets_received = 0
    last_check = datetime.now()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSaving and closing...")
        if RECORD_AUDIO and output_file:
            output_file.close()
