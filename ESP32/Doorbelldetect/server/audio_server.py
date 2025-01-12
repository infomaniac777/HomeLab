import socket
import wave
import struct
from datetime import datetime
import os

# UDP server configuration
UDP_IP = "0.0.0.0"
UDP_PORT = 3003

# Improved audio settings
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit
SAMPLE_RATE = 44100  # CD quality
BUFFER_SIZE = 1024  # Increased buffer

def create_wav_file():
    filename = "audio_recording.wav"
    wav_file = wave.open(filename, 'wb')
    wav_file.setnchannels(CHANNELS)
    wav_file.setsampwidth(SAMPLE_WIDTH)
    wav_file.setframerate(SAMPLE_RATE)
    return wav_file

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"Listening on port {UDP_PORT}")
    
    wav_file = create_wav_file()
    
    try:
        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE * SAMPLE_WIDTH)
            wav_file.writeframes(data)
            print(".", end="", flush=True)
            
    except KeyboardInterrupt:
        print("\nSaving recording...")
        wav_file.close()
        
if __name__ == "__main__":
    main()

