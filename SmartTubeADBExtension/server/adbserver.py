import subprocess
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import select
import platform
import distro
import os
import sys
import flask_monitoringdashboard as dashboard

PORT = int(os.getenv("PORT", "8123"))
ADB_DEVICE = os.getenv("ADB_DEVICE", "192.168.0.8:5555")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

app.logger.setLevel(logging.INFO)

# Create a persistent shell process (without closing pipes)
shell_process = subprocess.Popen(['bash'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def log_os_info():
    """Log OS and platform information and return it as JSON."""
    os_info = {
        'Operating System': platform.system(),
        'OS Version': platform.version(),
        'Platform': platform.platform(),
        'Architecture': platform.architecture(),
        'Machine': platform.machine(),
        'Processor': platform.processor()
    }
    # If the operating system is Linux, add distro info
    if platform.system().lower() == 'linux':
        os_info['Distro'] = {
            'Name': distro.name(),
            'Version': distro.version(),
            'Codename': distro.codename()
        }
    
    return os_info

def send_command(command):
    """Send a command to the persistent shell and capture output."""
    # Log the execution of the command
    app.logger.info(f"Executing: {command}")
    shell_process.stdin.write(f"{command}\n")
    shell_process.stdin.flush()

    stdout_data = []
    stderr_data = []

    # Use select to check if there's data available on stdout/stderr
    while True:
        ready_to_read, _, _ = select.select([shell_process.stdout, shell_process.stderr], [], [], 5)  # Timeout of 5 seconds

        if shell_process.stdout in ready_to_read:
            line = shell_process.stdout.readline().strip()
            if line:
                stdout_data.append(line)
        
        if shell_process.stderr in ready_to_read:
            line = shell_process.stderr.readline().strip()
            if line:
                stderr_data.append(line)

        # Break the loop if there's no more data to read
        if not ready_to_read:
            break

    stdout_join = "\n".join(stdout_data)
    stderr_join = "\n".join(stderr_data)

    # Log stdout and stderr
    if stdout_join:
        app.logger.info(f"ADB Command Output ({command}): {stdout_join}")
    
    if stderr_join:
        app.logger.warning(f"ADB Command Warning/Error ({command}): {stderr_join}")

    # Check for specific error patterns in stderr (optional)
    # Example: If you want to treat certain errors as fatal
    error_keywords = ["error", "failed", "not found"]
    for keyword in error_keywords:
        if keyword in stderr_join.lower():
            app.logger.error(f"Critical ADB Error detected: {stderr_join}")
            return False
    
    return True

def connect_adb_device():
    """Initial ADB commands to connect the device (if needed)."""
    adb_commands = [
        "adb kill-server",
        "adb start-server",
        f"adb connect {ADB_DEVICE}"
    ]

    # Execute each ADB command and log output/errors using send_command()
    for command in adb_commands:
        send_command(command)

def run_adb_command(video_url):
    """Run an ADB command asynchronously without waiting for output."""
    # Build the ADB command with single quotes around the URL
    adb_command = f'adb shell "am start -a android.intent.action.VIEW -d \'{video_url}\' -n com.teamsmart.videomanager.tv/com.liskovsoft.smartyoutubetv2.tv.ui.main.SplashActivity"'
    
    # Send the command using send_command()
    return send_command(adb_command)

@app.route('/', methods=['GET'])
def get_root():
    return jsonify(log_os_info()), 200


def clean_url(orig_url):
    return orig_url.replace("&list=WL", "")

# Webhook endpoint to receive video URL and trigger ADB command
@app.route('/play-video', methods=['POST'])
def play_video():
    data = request.get_json()

    # Check if 'url' is in the JSON body
    if 'url' not in data:
        app.logger.error("No URL provided")
        return jsonify({"error": "No URL provided"}), 400

    video_url = data['url']
    app.logger.info(f"Received video URL: {video_url}")
    video_url = clean_url(video_url)
    app.logger.info(f"Final video URL after cleaning: {video_url}")

    # Run the ADB command to play the video on SmartTubeNext
    if not run_adb_command(video_url):
        app.logger.warning('adb command failure, trying re-int adb connection...')
        connect_adb_device()
        app.logger.warning('Will retry adb now...')
        if not run_adb_command(video_url):
            app.logger.error('adb command failing in retry as well so exiting...')
            sys.exit(-1)

    return jsonify({"message": "Video playback triggered"}), 200

# Bind the monitoring dashboard to the app
dashboard.bind(app)

if __name__ == '__main__':
    app.logger.info('Starting script')

    # Connect ADB device (this will wait for 5 seconds)
    connect_adb_device()

    app.logger.info("Starting server")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=PORT, debug=True)