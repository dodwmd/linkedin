import asyncio
from nats.aio.client import Client as NATS
from shared_data import log
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class NatsManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.nc = NATS()
        return cls._instance

    async def connect(self):
        if not self.nc.is_connected:
            try:
                # Use the NATS_URL from .env file
                nats_url = os.getenv('NATS_URL', 'nats://nats:4222')
                await self.nc.connect(nats_url)
                log(f"Connected to NATS server at {nats_url}")
            except Exception as e:
                log(f"Failed to connect to NATS server: {str(e)}", "error")
                raise

    async def close(self):
        if self.nc.is_connected:
            await self.nc.close()
            log("Disconnected from NATS server")

    async def publish(self, subject, message):
        if not self.nc.is_connected:
            await self.connect()
        await self.nc.publish(subject, message.encode())

    async def subscribe(self, subject):
        if not self.nc.is_connected:
            await self.connect()
        await self.nc.subscribe(subject)

    async def get_message(self, subject, timeout=5):
        if not self.nc.is_connected:
            await self.connect()
        try:
            future = asyncio.Future()
            async def cb(msg):
                nonlocal future
                future.set_result(msg)
            
            sub = await self.nc.subscribe(subject, cb=cb)
            try:
                msg = await asyncio.wait_for(future, timeout=timeout)
                return subject, msg.data.decode()
            finally:
                await sub.unsubscribe()
        except asyncio.TimeoutError:
            return None, None

    @classmethod
    async def get_instance(cls):
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            await cls._instance.connect()
        return cls._instance
