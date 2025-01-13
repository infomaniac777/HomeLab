import socket
import wave
import time
from datetime import datetime
import os

# UDP server configuration
UDP_IP = "0.0.0.0"
UDP_PORT = 3003

# Match ESP32 settings
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit
SAMPLE_RATE = 44100
BUFFER_SIZE = 736  # Matches ESP32's buffer (1472/2 bytes)

def create_wav_file():
    filename = "audio_recording.wav"
    wav_file = wave.open(filename, 'wb')
    wav_file.setnchannels(CHANNELS)
    wav_file.setsampwidth(SAMPLE_WIDTH)
    wav_file.setframerate(SAMPLE_RATE)
    return wav_file, filename

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"Listening on port {UDP_PORT}")
    
    wav_file, filename = create_wav_file()
    packets = 0
    start_time = time.time()
    
    try:
        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE * SAMPLE_WIDTH)
            wav_file.writeframes(data)
            packets += 1
            
            if packets % 60 == 0:  # Show stats every ~second
                elapsed = time.time() - start_time
                rate = packets / elapsed
                print(f"\rRate: {rate:.1f} packets/s", end="", flush=True)
            
    except KeyboardInterrupt:
        print(f"\nReceived {packets} packets in {time.time()-start_time:.1f}s")
        wav_file.close()
        print(f"\nSaved to {filename}")
        
if __name__ == "__main__":
    main()

