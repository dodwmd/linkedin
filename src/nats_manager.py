import nats
from nats.errors import ConnectionClosedError, TimeoutError
from shared_data import log
import os
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

class NatsManager:
    _instance = None

    def __init__(self):
        self._nc = None
        self._nats_url = os.getenv('NATS_URL', 'nats://nats:4222')

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def connect(self):
        if not self.is_connected():
            try:
                self._nc = await nats.connect(self._nats_url)
                log(f"Connected to NATS server at {self._nats_url}")
            except Exception as e:
                log(f"Failed to connect to NATS server: {str(e)}", "error")
                raise

    async def publish(self, subject, message):
        if not self.is_connected():
            await self.connect()
        try:
            await self._nc.publish(subject, message.encode())
            log(f"Published message to {subject}")
        except ConnectionClosedError:
            log("NATS connection closed. Attempting to reconnect...", "warning")
            await self.connect()
            await self._nc.publish(subject, message.encode())
        except Exception as e:
            log(f"Error publishing message to NATS: {str(e)}", "error")
            raise

    async def subscribe(self, subject, callback):
        if not self.is_connected():
            await self.connect()
        try:
            await self._nc.subscribe(subject, cb=callback)
            log(f"Subscribed to {subject}")
        except Exception as e:
            log(f"Error subscribing to NATS subject: {str(e)}", "error")
            raise

    async def close(self):
        if self.is_connected():
            try:
                await self._nc.close()
                self._nc = None
                log("Disconnected from NATS server")
            except Exception as e:
                log(f"Error closing NATS connection: {str(e)}", "error")

    def is_connected(self):
        return self._nc is not None and self._nc.is_connected
