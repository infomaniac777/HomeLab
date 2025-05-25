import tinytuya
import time
import os
import socket
import logging
import json
import threading
from prometheus_client import start_http_server, Gauge, Counter

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# Prometheus metrics
voltage_gauge = Gauge('tuya_voltage_volts', 'Voltage measured by the Tuya device', ['device_id', 'device_name'])
current_gauge = Gauge('tuya_current_amperes', 'Current measured by the Tuya device', ['device_id', 'device_name'])
power_gauge = Gauge('tuya_power_watts', 'Power measured by the Tuya device', ['device_id', 'device_name'])
tuya_exporter_issues_total = Counter('tuya_exporter_issues_total', 'Total number of issues encountered by the exporter', ['device_name', 'level'])

# Global store for device configurations and tinytuya device objects
device_objects = {}
device_configs_map = {}


def set_gauges_to_nan(device_id, device_name):
    """Sets all Prometheus gauges to NaN for the given device."""
    logger.debug(f"Setting gauges to NaN for device_id: {device_id}, device_name: {device_name}")
    voltage_gauge.labels(device_id=device_id, device_name=device_name).set(float('nan'))
    current_gauge.labels(device_id=device_id, device_name=device_name).set(float('nan'))
    power_gauge.labels(device_id=device_id, device_name=device_name).set(float('nan'))


def update_metrics_persistent(device_id_to_update):
    """
    Connects to the Tuya device using a persistent connection (if available),
    fetches data, and updates Prometheus metrics.
    Attempts to re-initialize connection if it fails.
    """
    device_config = device_configs_map.get(device_id_to_update)
    if not device_config:
        logger.error(f"No configuration found for device_id {device_id_to_update}")
        tuya_exporter_issues_total.labels(device_name="unknown", level="error").inc()
        return

    device_name = device_config['name']
    device_ip = device_config['ip']
    device_key = device_config['key']
    device_version = device_config['version']

    d = device_objects.get(device_id_to_update)

    if d is None:
        logger.info(f"Attempting to establish persistent connection to {device_name} ({device_id_to_update} @ {device_ip})...")
        try:
            d = tinytuya.OutletDevice(
                dev_id=device_id_to_update,
                address=device_ip,
                local_key=device_key,
                version=device_version,
                persist=True,
                connection_timeout=5
            )
            logger.info(f"Connection object created for {device_name}. Waiting a moment for connection to establish...")
            time.sleep(2) 
            device_objects[device_id_to_update] = d
            logger.info(f"Persistent connection ready for {device_name}.")
        except Exception as e:
            logger.error(f"Failed to initialize persistent connection for device {device_name} ({device_id_to_update}): {e}")
            tuya_exporter_issues_total.labels(device_name=device_name, level="error").inc()
            device_objects[device_id_to_update] = None 
            set_gauges_to_nan(device_id_to_update, device_name)
            return

    try:
        d.updatedps(index=[18, 19, 20], nowait=False)
        status = d.status(nowait=False)
        logger.debug(f"Status for {device_name} ({device_id_to_update} @ {device_ip}): {status}")

        if status and 'dps' in status:
            dps = status['dps']
            voltage, current, power = None, None, None

            # Try to get voltage from DPS '20'
            if '20' in dps:
                voltage = dps['20'] / 10.0
            else:
                logger.warning(f"DPS key '20' (voltage) not found for {device_name}. Available DPS: {dps}")
                tuya_exporter_issues_total.labels(device_name=device_name, level="warning").inc()
            
            # Try to get current from DPS '18'
            if '18' in dps:
                current = dps['18'] / 1000.0
            else:
                logger.warning(f"DPS key '18' (current) not found for {device_name}. Available DPS: {dps}")
                tuya_exporter_issues_total.labels(device_name=device_name, level="warning").inc()
            
            # Try to get power from DPS '19'
            if '19' in dps:
                power = dps['19'] / 10.0
            else:
                logger.warning(f"DPS key '19' (power) not found for {device_name}. Available DPS: {dps}")
                tuya_exporter_issues_total.labels(device_name=device_name, level="warning").inc()

            # Set gauges based on parsed values (or NaN if parsing failed for a specific metric)
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
            tuya_exporter_issues_total.labels(device_name=device_name, level="error").inc()
            if d:
                try:
                    d.close()
                except Exception as close_err:
                    logger.error(f"Error closing connection for {device_name} after device error: {close_err}")
                    tuya_exporter_issues_total.labels(device_name=device_name, level="error").inc()
            device_objects[device_id_to_update] = None
            set_gauges_to_nan(device_id_to_update, device_name)
            return
        else:
            logger.warning(f"Failed to get valid status or DPS for device {device_name} ({device_id_to_update}). Status: {status}")
            tuya_exporter_issues_total.labels(device_name=device_name, level="warning").inc()
            set_gauges_to_nan(device_id_to_update, device_name)

    except (ConnectionResetError, socket.timeout, tinytuya.DecodeError) as e:
        logger.warning(f"Network/Decode error for {device_name} ({device_id_to_update}): {e}. Attempting re-initialization on next cycle.")
        tuya_exporter_issues_total.labels(device_name=device_name, level="warning").inc()
        if d:
            try:
                d.close()
            except Exception as close_err:
                logger.error(f"Error closing connection for {device_name} during {type(e).__name__}: {close_err}")
                tuya_exporter_issues_total.labels(device_name=device_name, level="error").inc()
        device_objects[device_id_to_update] = None
        set_gauges_to_nan(device_id_to_update, device_name)
    except Exception as e:
        logger.error(f"Unexpected error processing device {device_name} ({device_id_to_update}): {e}", exc_info=True)
        tuya_exporter_issues_total.labels(device_name=device_name, level="error").inc()
        if d:
            try:
                d.close()
            except Exception as close_err:
                logger.error(f"Error closing connection for {device_name} during generic Exception: {close_err}")
                tuya_exporter_issues_total.labels(device_name=device_name, level="error").inc()
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
            tuya_exporter_issues_total.labels(device_name="config_loading", level="error").inc()
            DEVICES_CONFIG_LIST = [] # Reset to empty list
    except FileNotFoundError:
        logger.error(f"Error: Devices configuration file not found at {devices_config_path}. Please create it or set TUYA_DEVICES_CONFIG_PATH.")
        tuya_exporter_issues_total.labels(device_name="config_loading", level="error").inc()
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {devices_config_path}: {e}")
        tuya_exporter_issues_total.labels(device_name="config_loading", level="error").inc()
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading {devices_config_path}: {e}")
        tuya_exporter_issues_total.labels(device_name="config_loading", level="error").inc()

    if DEVICES_CONFIG_LIST:
        for dev_conf in DEVICES_CONFIG_LIST:
            if all(k in dev_conf for k in ('id', 'name', 'ip', 'key', 'version')):
                device_objects[dev_conf['id']] = None
                device_configs_map[dev_conf['id']] = dev_conf
            else:
                logger.warning(f"Skipping device due to missing keys in configuration: {dev_conf.get('name', 'Unnamed Device')}")
                tuya_exporter_issues_total.labels(device_name=dev_conf.get('name', 'unknown_name'), level="warning").inc()

        logger.info(f"Successfully loaded {len(device_configs_map)} Tuya devices to monitor from {devices_config_path}:")
        for dev_id, dev_info in device_configs_map.items():
            logger.info(f"  ID: {dev_info['id']}, Name: {dev_info['name']}, IP: {dev_info['ip']}, Key: {'*' * len(dev_info['key'])}, Version: {dev_info['version']}")
    else:
        logger.info(f"No devices loaded from {devices_config_path}. The exporter will run but monitor no devices.")

    start_http_server(exporter_port)
    logger.info(f"Prometheus exporter started on port {exporter_port}")

    while True:
        threads = []
        if not DEVICES_CONFIG_LIST:
            logger.info(f"No devices configured. Waiting {scrape_interval} seconds.")
        else:
            for device_conf_main_loop in DEVICES_CONFIG_LIST:
                device_id = device_conf_main_loop['id']
                device_name = device_conf_main_loop['name']
                logger.info(f"Creating thread to query {device_name} ({device_id})...")
                thread = threading.Thread(target=update_metrics_persistent, args=(device_id,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()
        
        logger.info(f"--- Completed polling cycle for all devices. Waiting {scrape_interval} seconds. ---")
        time.sleep(scrape_interval)
