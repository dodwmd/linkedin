import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from shared_data import log

# Load environment variables from .env file
load_dotenv()

class MySQLManager:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self._db_config = {
            'host': os.getenv('MYSQL_HOST', 'mysql'),
            'database': os.getenv('MYSQL_DATABASE', 'linkedin_db'),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'rootpassword')
        }

    @property
    def db_config(self):
        return self._db_config

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True, buffered=True)
                log("Successfully connected to MySQL database")
            else:
                log("Failed to connect to MySQL database", "error")
        except Error as e:
            log(f"Error while connecting to MySQL: {e}", "error")
            raise

    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.connection and self.connection.is_connected():
            self.connection.close()
            log("MySQL connection closed")

    def execute_query(self, query, params=None):
        try:
            if not self.connection or not self.connection.is_connected():
                log("MySQL connection is not established. Reconnecting...", "warning")
                self.connect()
            
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("SHOW"):
                result = self.cursor.fetchall()
            else:
                self.connection.commit()
                result = [{"affected_rows": self.cursor.rowcount}]
            
            log(f"Query executed successfully: {query[:50]}...")
            return result
        except Error as e:
            log(f"Error executing query: {e}", "error")
            raise
        finally:
            self.cursor.reset()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
