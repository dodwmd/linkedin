import aiomysql
from mysql.connector import Error
import os
from dotenv import load_dotenv
from shared_data import log

# Load environment variables from .env file
load_dotenv()

class MySQLManager:
    def __init__(self):
        self.pool = None
        self.db_config = {
            'host': os.getenv('MYSQL_HOST', 'mysql'),
            'db': os.getenv('MYSQL_DATABASE', 'linkedin_db'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'rootpassword')
        }

    async def connect(self):
        if self.pool is None or self.pool.closed:
            try:
                self.pool = await aiomysql.create_pool(**self.db_config)
                log("Successfully connected to MySQL database")
            except Exception as e:
                log(f"Error while connecting to MySQL: {e}", "error")
                raise

    async def disconnect(self):
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            log("MySQL connection closed")

    async def execute_query(self, query, params=None):
        if self.pool is None or self.pool.closed:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                try:
                    await cur.execute(query, params)
                    if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("SHOW"):
                        result = await cur.fetchall()
                    else:
                        await conn.commit()
                        result = [{"affected_rows": cur.rowcount}]
                    
                    log(f"Query executed successfully: {query[:50]}...")
                    return result
                except Exception as e:
                    log(f"Error executing query: {e}", "error")
                    raise

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
