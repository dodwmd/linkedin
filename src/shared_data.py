import queue
from datetime import datetime
import threading
from queue import Queue
import json

# Global variables for statistics
profiles_scanned = 0
companies_scanned = 0

# Queue to store crawler activities
activity_queue = Queue(maxsize=100)

# Status variables for NATS and MySQL connections
nats_status = "Not connected"
mysql_status = "Not connected"

# SocketIO instance (to be set by the app)
socketio = None

class CrawlerState:
    def __init__(self):
        self._running = False
        self._stop_requested = False
        self._lock = threading.Lock()

    def is_running(self):
        with self._lock:
            return self._running

    def set_running(self):
        with self._lock:
            self._running = True
            self._stop_requested = False

    def set_stopped(self):
        with self._lock:
            self._running = False
            self._stop_requested = False

    def is_stop_requested(self):
        with self._lock:
            return self._stop_requested

    def set_stop_requested(self):
        with self._lock:
            self._stop_requested = True

# Function to add log entry to queue
def add_log_entry(message, level="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level.upper()}] {message}"
    print(log_entry)  # Print to console
    activity_queue.put(log_entry)  # Add to queue for Flask UI
    if socketio:
        socketio.emit('log_update', {'log': log_entry}, namespace='/crawler')

# Updated log function
def log(message, level="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level.upper()}] {message}"
    print(log_entry)  # Print to console
    
    log_data = {
        'timestamp': timestamp,
        'level': level.upper(),
        'message': message
    }
    
    activity_queue.put(json.dumps(log_data))  # Add to queue for Flask UI
    if socketio:
        socketio.emit('log_update', log_data, namespace='/crawler')

def set_nats_status(status):
    global nats_status
    nats_status = status
    add_log_entry(f"NATS status changed to: {status}", "info")

def set_mysql_status(status):
    global mysql_status
    mysql_status = status
    add_log_entry(f"MySQL status changed to: {status}", "info")

def increment_profiles_scanned():
    global profiles_scanned
    profiles_scanned += 1
    log(f"Profiles scanned: {profiles_scanned}")

def increment_companies_scanned():
    global companies_scanned
    companies_scanned += 1
    log(f"Companies scanned: {companies_scanned}")

# Update this function
def emit_crawler_update(data):
    log(f"Crawler update: {data}")
    if socketio:
        socketio.emit('crawler_update', data, namespace='/crawler')

# Add this function to set the SocketIO instance
def set_socketio(sio):
    global socketio
    socketio = sio
