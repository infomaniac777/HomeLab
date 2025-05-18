import tinytuya
import time
import os
import socket
import logging
import json  # Added
from prometheus_client import start_http_server, Gauge

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Prometheus metrics
voltage_gauge = Gauge('tuya_voltage_volts', 'Voltage measured by the Tuya device', ['device_id', 'device_name'])
current_gauge = Gauge('tuya_current_amperes', 'Current measured by the Tuya device', ['device_id', 'device_name'])
power_gauge = Gauge('tuya_power_watts', 'Power measured by the Tuya device', ['device_id', 'device_name'])

# Global store for device configurations and tinytuya device objects
device_objects = {}
device_configs_map = {}

# --- Helper function to set gauges to 0 ---
def set_gauges_to_nan(device_id, device_name): # Renamed function
    """Sets all Prometheus gauges to NaN for the given device."""
    logger.debug(f"Setting gauges to NaN for device_id: {device_id}, device_name: {device_name}")
    voltage_gauge.labels(device_id=device_id, device_name=device_name).set(float('nan'))
    current_gauge.labels(device_id=device_id, device_name=device_name).set(float('nan'))
    power_gauge.labels(device_id=device_id, device_name=device_name).set(float('nan'))

# --- Modified update_metrics function ---
def update_metrics_persistent(device_id_to_update): # Renamed to avoid conflict if old code was pasted
    """
    Connects to the Tuya device using a persistent connection (if available),
    fetches data, and updates Prometheus metrics.
    Attempts to re-initialize connection if it fails.
    """
    device_config = device_configs_map.get(device_id_to_update)
    if not device_config:
        logger.error(f"No configuration found for device_id {device_id_to_update}")
        return

    device_name = device_config['name']
    device_ip = device_config['ip'] # Defined from device_config
    device_key = device_config['key'] # Defined from device_config
    device_version = device_config['version'] # Defined from device_config

    d = device_objects.get(device_id_to_update)

    if d is None:
        logger.info(f"Attempting to establish persistent connection to {device_name} ({device_id_to_update} @ {device_ip})...")
        try:
            d = tinytuya.OutletDevice(
                dev_id=device_id_to_update,
                address=device_ip,
                local_key=device_key,
                version=device_version,
                persist=True  # Enable persistent connection
            )
            logger.info(f"Connection object created for {device_name}. Waiting a moment for connection to establish...")
            time.sleep(2) 
            device_objects[device_id_to_update] = d
            logger.info(f"Persistent connection ready for {device_name}.")
        except Exception as e:
            logger.error(f"Failed to initialize persistent connection for device {device_name} ({device_id_to_update}): {e}")
            device_objects[device_id_to_update] = None 
            set_gauges_to_nan(device_id_to_update, device_name)
            return

    try:
        status = d.status()
        logger.debug(f"Status for {device_name} ({device_id_to_update} @ {device_ip}): {status}")

        if status and 'dps' in status:
            dps = status['dps']
            voltage, current, power = None, None, None

            if '20' in dps and '18' in dps and '19' in dps:
                voltage = dps['20'] / 10.0
                current = dps['18'] / 1000.0
                power = dps['19'] / 10.0
            elif '6' in dps and '4' in dps and '5' in dps:
                voltage = dps['6'] / 10.0
                current = dps['4'] / 1000.0
                power = dps['5'] / 10.0
            elif '4' in dps and '3' in dps and '2' in dps:
                voltage = dps['4'] / 10.0
                current = dps['3'] / 1000.0
                power = dps['2']
            elif 'voltage' in dps and 'current' in dps and 'power' in dps:
                voltage = dps['voltage']
                current = dps['current']
                power = dps['power']
            else:
                logger.warning(f"Could not find expected DPS keys for {device_name}. DPS: {dps}")
                set_gauges_to_nan(device_id_to_update, device_name)
                # No return here, will proceed to set NaN for any values not found

            if voltage is not None:
                voltage_gauge.labels(device_id=device_id_to_update, device_name=device_name).set(voltage)
            else:
                voltage_gauge.labels(device_id=device_id_to_update, device_name=device_name).set(float('nan'))

            if current is not None:
                current_gauge.labels(device_id=device_id_to_update, device_name=device_name).set(current)
            else:
                current_gauge.labels(device_id=device_id_to_update, device_name=device_name).set(float('nan'))

            if power is not None:
                power_gauge.labels(device_id=device_id_to_update, device_name=device_name).set(power)
            else:
                power_gauge.labels(device_id=device_id_to_update, device_name=device_name).set(float('nan'))

        elif status and status.get('Error'):
            error_msg = status.get('Error')
            payload = status.get('Payload') 
            logger.error(f"Device {device_name} ({device_id_to_update}) returned an error in status: {error_msg}. Payload: {payload}")
            if d:
                try:
                    d.close()
                except Exception as close_err:
                    logger.error(f"Error closing connection for {device_name} after device error: {close_err}")
            device_objects[device_id_to_update] = None
            set_gauges_to_nan(device_id_to_update, device_name)
            return
        else:
            logger.warning(f"Failed to get valid status or DPS for device {device_name} ({device_id_to_update}). Status: {status}")
            set_gauges_to_nan(device_id_to_update, device_name)

    except (ConnectionResetError, socket.timeout, tinytuya.DecodeError) as e:
        logger.warning(f"Network/Decode error for {device_name} ({device_id_to_update}): {e}. Attempting re-initialization on next cycle.")
        if d:
            try:
                d.close()
            except Exception as close_err:
                logger.error(f"Error closing connection for {device_name} during {type(e).__name__}: {close_err}")
        device_objects[device_id_to_update] = None
        set_gauges_to_nan(device_id_to_update, device_name)
    except Exception as e:
        logger.error(f"Unexpected error processing device {device_name} ({device_id_to_update}): {e}", exc_info=True)
        if d:
            try:
                d.close()
            except Exception as close_err:
                logger.error(f"Error closing connection for {device_name} during generic Exception: {close_err}")
        device_objects[device_id_to_update] = None
        set_gauges_to_nan(device_id_to_update, device_name)

if __name__ == '__main__':
    exporter_port = int(os.getenv('EXPORTER_PORT', 9876))
    scrape_interval = int(os.getenv('SCRAPE_INTERVAL', 15))
    devices_config_path = os.getenv('TUYA_DEVICES_CONFIG_PATH', 'devices.json')

    DEVICES_CONFIG_LIST = []
    try:
        with open(devices_config_path, 'r') as f:
            DEVICES_CONFIG_LIST = json.load(f)
        if not isinstance(DEVICES_CONFIG_LIST, list):
            logger.error(f"Error: Content of {devices_config_path} is not a JSON list.")
            DEVICES_CONFIG_LIST = [] # Reset to empty list
    except FileNotFoundError:
        logger.error(f"Error: Devices configuration file not found at {devices_config_path}. Please create it or set TUYA_DEVICES_CONFIG_PATH.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {devices_config_path}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading {devices_config_path}: {e}")

    # Populate device_objects and device_configs_map
    if DEVICES_CONFIG_LIST:
        for dev_conf in DEVICES_CONFIG_LIST:
            if all(k in dev_conf for k in ('id', 'name', 'ip', 'key', 'version')):
                device_objects[dev_conf['id']] = None
                device_configs_map[dev_conf['id']] = dev_conf
            else:
                logger.warning(f"Skipping device due to missing keys in configuration: {dev_conf.get('name', 'Unnamed Device')}")

        logger.info(f"Successfully loaded {len(device_configs_map)} Tuya devices to monitor from {devices_config_path}:")
        for dev_id, dev_info in device_configs_map.items():
            logger.info(f"  ID: {dev_info['id']}, Name: {dev_info['name']}, IP: {dev_info['ip']}, Key: {'*' * len(dev_info['key'])}, Version: {dev_info['version']}")
    else:
        logger.info(f"No devices loaded from {devices_config_path}. The exporter will run but monitor no devices.")

    start_http_server(exporter_port)
    logger.info(f"Prometheus exporter started on port {exporter_port}")

    while True:
        for device_conf_main_loop in DEVICES_CONFIG_LIST: 
            logger.info(f"Querying {device_conf_main_loop['name']} ({device_conf_main_loop['id']})...")
            update_metrics_persistent(device_conf_main_loop['id']) 
        
        logger.info(f"--- Completed polling cycle. Waiting {scrape_interval} seconds. ---")
        time.sleep(scrape_interval)
