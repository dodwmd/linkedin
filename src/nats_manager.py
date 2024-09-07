import asyncio
from nats.aio.client import Client as NATS


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
            await self.nc.connect()

    async def close(self):
        if self.nc.is_connected:
            await self.nc.close()

    @classmethod
    async def get_instance(cls):
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            await cls._instance.connect()
        return cls._instance
