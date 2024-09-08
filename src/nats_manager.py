import nats
from nats.errors import ConnectionClosedError, TimeoutError
from shared_data import log
import os
from dotenv import load_dotenv
import eventlet

# Load environment variables
load_dotenv()

class NatsManager:
    _instance = None
    _nc = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def connect(self):
        if self._nc is None or not self._nc.is_connected:
            try:
                nats_url = os.getenv('NATS_URL', 'nats://nats:4222')
                self._nc = eventlet.spawn(nats.connect, nats_url).wait()
                log(f"Connected to NATS server at {nats_url}")
            except Exception as e:
                log(f"Failed to connect to NATS server: {str(e)}", "error")
                raise

    def publish(self, subject, message):
        if not self._nc or not self._nc.is_connected:
            self.connect()
        try:
            eventlet.spawn(self._nc.publish, subject, message.encode()).wait()
        except ConnectionClosedError:
            log("NATS connection closed. Attempting to reconnect...", "warning")
            self.connect()
            eventlet.spawn(self._nc.publish, subject, message.encode()).wait()
        except Exception as e:
            log(f"Error publishing message to NATS: {str(e)}", "error")
            raise

    def subscribe(self, subject):
        if not self._nc or not self._nc.is_connected:
            self.connect()
        try:
            return eventlet.spawn(self._nc.subscribe, subject).wait()
        except Exception as e:
            log(f"Error subscribing to NATS subject: {str(e)}", "error")
            raise

    def request(self, subject, message, timeout=5):
        if not self._nc or not self._nc.is_connected:
            self.connect()
        try:
            response = eventlet.spawn(self._nc.request, subject, message.encode(), timeout=timeout).wait()
            return response.data.decode()
        except TimeoutError:
            log(f"Timeout waiting for response on subject: {subject}", "warning")
            return None
        except Exception as e:
            log(f"Error making request to NATS: {str(e)}", "error")
            raise

    def close(self):
        if self._nc and self._nc.is_connected:
            try:
                eventlet.spawn(self._nc.close).wait()
                log("Disconnected from NATS server")
            except Exception as e:
                log(f"Error closing NATS connection: {str(e)}", "error")

    def is_connected(self):
        return self._nc is not None and self._nc.is_connected
