import nats
from nats.errors import ConnectionClosedError, TimeoutError
from shared_data import log
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NatsManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.nc = None
        return cls._instance

    def connect(self):
        if self.nc is None or not self.nc.is_connected:
            try:
                # Use the NATS_URL from .env file
                nats_url = os.getenv('NATS_URL', 'nats://nats:4222')
                self.nc = nats.connect(nats_url)
                log(f"Connected to NATS server at {nats_url}")
            except Exception as e:
                log(f"Failed to connect to NATS server: {str(e)}", "error")
                raise

    def publish(self, subject, message):
        if not self.nc or not self.nc.is_connected:
            self.connect()
        try:
            self.nc.publish(subject, message.encode())
        except ConnectionClosedError:
            log("NATS connection closed. Attempting to reconnect...", "warning")
            self.connect()
            self.nc.publish(subject, message.encode())
        except Exception as e:
            log(f"Error publishing message to NATS: {str(e)}", "error")
            raise

    def subscribe(self, subject):
        if not self.nc or not self.nc.is_connected:
            self.connect()
        try:
            return self.nc.subscribe(subject)
        except Exception as e:
            log(f"Error subscribing to NATS subject: {str(e)}", "error")
            raise

    def request(self, subject, message, timeout=5):
        if not self.nc or not self.nc.is_connected:
            self.connect()
        try:
            response = self.nc.request(subject, message.encode(), timeout=timeout)
            return response.data.decode()
        except TimeoutError:
            log(f"Timeout waiting for response on subject: {subject}", "warning")
            return None
        except Exception as e:
            log(f"Error making request to NATS: {str(e)}", "error")
            raise

    def close(self):
        if self.nc and self.nc.is_connected:
            try:
                self.nc.close()
                log("Disconnected from NATS server")
            except Exception as e:
                log(f"Error closing NATS connection: {str(e)}", "error")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
