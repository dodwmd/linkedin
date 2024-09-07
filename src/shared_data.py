import queue
from datetime import datetime
import threading

# Global variables for statistics
profiles_scanned = 0
companies_scanned = 0

# Queue to store crawler activities
activity_queue = queue.Queue()

# Status variables for NATS and MySQL connections
nats_status = "Not connected"
mysql_status = "Not connected"


class CrawlerState:
    def __init__(self):
        self._running = False
        self._stop_requested = threading.Event()
        self._lock = threading.Lock()

    def is_running(self):
        with self._lock:
            return self._running

    def set_running(self):
        with self._lock:
            self._running = True
            self._stop_requested.clear()

    def set_stopped(self):
        with self._lock:
            self._running = False
            self._stop_requested.clear()

    def set_stop_requested(self):
        self._stop_requested.set()

    def is_stop_requested(self):
        return self._stop_requested.is_set()


# Function to add log entry to queue
def add_log_entry(message, level="info"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level.upper()}] {message}"
    print(log_entry)  # Print to console
    activity_queue.put(log_entry)  # Add to queue for Flask UI


# Updated log function
def log(message, level="info"):
    add_log_entry(message, level)


def set_nats_status(status):
    global nats_status
    nats_status = status
    add_log_entry(f"NATS status changed to: {status}", "info")


def set_mysql_status(status):
    global mysql_status
    mysql_status = status
    add_log_entry(f"MySQL status changed to: {status}", "info")
