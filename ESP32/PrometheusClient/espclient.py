from prometheus_client import start_http_server, Gauge
import requests
import time
import logging
import signal
import os
import sys

# Configuration from environment variables
ESP32_IP = os.getenv('ESP32_IP', '192.168.0.51')
PORT = int(os.getenv('PORT', '8700'))
INTERVAL = int(os.getenv('INTERVAL', '5'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Prometheus gauge metrics
temperature_gauge = Gauge('esp32_temperature_celsius', 'Temperature from ESP32 sensor')
health_gauge = Gauge('esp32_client_health', 'Health status of ESP32 client')

def signal_handler(signum, frame):
    logger.info("Shutdown signal received, exiting...")
    sys.exit(0)

def get_temperature():
    try:
        response = requests.get(
            f"http://{ESP32_IP}/temperature",
            timeout=5
        )
        response.raise_for_status()
        temp = response.json()["temperature"]
        health_gauge.set(1)
        return temp
    except Exception as e:
        logger.error(f"Error fetching temperature: {e}")
        health_gauge.set(0)
        return None

def main():
    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Start Prometheus HTTP server
    start_http_server(PORT)
    logger.info(f"Server started on port {PORT}")
    logger.info(f"Monitoring ESP32 at {ESP32_IP}")

    # Main loop
    while True:
        temp = get_temperature()
        if temp is not None:
            temperature_gauge.set(temp)
            logger.debug(f"Temperature recorded: {temp}°C")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()