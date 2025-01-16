import asyncio
import websockets
import wave
from datetime import datetime

# Configuration
WS_PORT = 3003
RATE_INTERVAL = 1
SAMPLE_RATE = 44100
CHANNELS = 1
SAMPLE_WIDTH = 2
BUFFER_SIZE = 1024

# State variables
packets_received = 0
last_check = datetime.now()
output_file = None
total_disconnected = 0

async def audio_server(websocket):  # Removed path parameter
    global packets_received, last_check
    print("Client connected")
    
    try:
        async for message in websocket:
            output_file.writeframes(message)
            packets_received += 1
            
            now = datetime.now()
            if (now - last_check).total_seconds() >= RATE_INTERVAL:
                rate = packets_received / RATE_INTERVAL
                print(f"Rate: {rate:.1f} packets/s")
                packets_received = 0
                last_check = now
                
    except websockets.exceptions.ConnectionClosed:
        total_disconnected += 1
        print("Client disconnected, total: ", total_disconnected)

        

def init_wav_file():
    global output_file
    output_file = wave.open("audio_recording.wav", "wb")
    output_file.setnchannels(CHANNELS)
    output_file.setsampwidth(SAMPLE_WIDTH)
    output_file.setframerate(SAMPLE_RATE)

async def main():
    init_wav_file()
    async with websockets.serve(audio_server, "0.0.0.0", WS_PORT):
        print(f"WebSocket server listening on port {WS_PORT}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    packets_received = 0
    last_check = datetime.now()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSaving and closing...")
        if output_file:
            output_file.close()
