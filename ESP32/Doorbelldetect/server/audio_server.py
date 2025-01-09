import socket
import wave
import struct

# UDP server configuration
UDP_IP = "0.0.0.0"  # Listen on all available interfaces
UDP_PORT = 3003

# Audio file configuration
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit audio
SAMPLE_RATE = 16000

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening on port {UDP_PORT}")

# Create WAV file
with wave.open("recorded_audio.wav", 'wb') as wav_file:
    wav_file.setnchannels(CHANNELS)
    wav_file.setsampwidth(SAMPLE_WIDTH)
    wav_file.setframerate(SAMPLE_RATE)
    
    try:
        while True:
            data, addr = sock.recvfrom(2048)  # Buffer size
            wav_file.writeframes(data)
            print("Received audio chunk")
    except KeyboardInterrupt:
        print("\nRecording stopped")

