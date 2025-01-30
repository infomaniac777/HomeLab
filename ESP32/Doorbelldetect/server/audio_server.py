import threading
import queue
from websocket_server import WebsocketServer
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
BUFFER_DURATION = 3  # seconds
BUFFER_SIZE_CLASSIFY = SAMPLE_RATE * SAMPLE_WIDTH *  CHANNELS * BUFFER_DURATION
RECORD_AUDIO = False
CONFIDENCE_THRESHOLD = 0.8

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

class AudioProcessor:
    def __init__(self):
        self.audio_queue = queue.Queue(maxsize=100)
        self.packet_stats = {'count': 0, 'bytes': 0, 'last_check': datetime.now()}
        self.server = WebsocketServer(port=WS_PORT, host='0.0.0.0')
        self.sliding_buffer = np.zeros(BUFFER_SIZE_CLASSIFY * 2, dtype=np.int16)  # 2x size for overlap
        self.buffer_position = 0
        self.overlap = BUFFER_SIZE_CLASSIFY // 2  # 50% overlap
        
    def new_client(self, client, server):
        logger.info(f"New client connected. ID: {client['id']}")
        
    def client_left(self, client, server):
        logger.info(f"Client disconnected. ID: {client['id']}")
        
    def message_received(self, client, server, message):
        try:
            # Handle raw binary data directly
            if isinstance(message, bytes):
                binary_data = message
            else:
                # For backwards compatibility
                binary_data = bytes(message, encoding='latin1')
            
            self.update_stats(len(binary_data))
            self.audio_queue.put(binary_data)
        except Exception as e:
            logger.error(f"Message processing error: {e}")
        
    def update_stats(self, message_size):
        now = datetime.now()
        self.packet_stats['count'] += 1
        self.packet_stats['bytes'] += message_size
        
        if (now - self.packet_stats['last_check']).total_seconds() >= PACKET_STATS_INTERVAL:
            elapsed = (now - self.packet_stats['last_check']).total_seconds()
            pps = self.packet_stats['count'] / elapsed
            bps = self.packet_stats['bytes'] / elapsed
            logger.info(f"Packet Rate: {pps:.2f} p/s, Data Rate: {(bps * 8)/1024:.2f} Kbps")
            
            self.packet_stats['count'] = 0
            self.packet_stats['bytes'] = 0
            self.packet_stats['last_check'] = now
            
    def classifier_thread(self):
        while True:
            try:
                message = self.audio_queue.get()
                if not isinstance(message, bytes):
                    logger.error(f"Invalid message type: {type(message)}")
                    continue
                
                # Convert bytes to numpy array
                audio_chunk = np.frombuffer(message, dtype=np.int16)
                chunk_size = len(audio_chunk)
                
                # Add to sliding buffer
                if self.buffer_position + chunk_size > len(self.sliding_buffer):
                    # Buffer wrap-around
                    self.sliding_buffer = np.roll(self.sliding_buffer, -chunk_size)
                    self.sliding_buffer[-chunk_size:] = audio_chunk
                else:
                    self.sliding_buffer[self.buffer_position:self.buffer_position + chunk_size] = audio_chunk
                    self.buffer_position += chunk_size
                
                # Process when we have enough data
                if self.buffer_position >= BUFFER_SIZE_CLASSIFY:
                    # Create WAV buffer for classification
                    wav_buffer = io.BytesIO()
                    wav_buffer.write(create_wav_header(SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH))
                    wav_buffer.write(self.sliding_buffer[:BUFFER_SIZE_CLASSIFY].tobytes())
                    
                    # Update WAV header
                    wav_buffer.seek(RIFF_SIZE_OFFSET)
                    wav_buffer.write(struct.pack('<I', BUFFER_SIZE_CLASSIFY + 36))
                    wav_buffer.seek(DATA_SIZE_OFFSET)
                    wav_buffer.write(struct.pack('<I', BUFFER_SIZE_CLASSIFY))
                    
                    # Classify
                    wav_buffer.seek(0)
                    class_name, confidence = classify_wav(wav_buffer)
                    logger.info(f"Predicted class: {class_name} (confidence: {confidence:.2%})")
                    if class_name and confidence > CONFIDENCE_THRESHOLD:
                        if class_name == 'Music':
                            send_detection(class_name, confidence)
                    
                    # Slide window by overlap amount
                    self.sliding_buffer = np.roll(self.sliding_buffer, -self.overlap)
                    self.buffer_position -= self.overlap
                    
            except Exception as e:
                logger.error(f"Classification error: {e}")

def main():
    processor = AudioProcessor()
    
    # Start classifier thread
    classifier = threading.Thread(
        target=processor.classifier_thread,
        daemon=True
    )
    classifier.start()
    
    # Setup WebSocket server
    processor.server.set_fn_new_client(processor.new_client)
    processor.server.set_fn_client_left(processor.client_left)
    processor.server.set_fn_message_received(processor.message_received)
    
    logger.info(f"WebSocket server starting on port {WS_PORT}")
    processor.server.run_forever()

if __name__ == "__main__":
    main()
