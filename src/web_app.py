import time
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from mysql_manager import MySQLManager
from shared_data import log

def wait_for_mysql():
    max_retries = 30
    retry_interval = 2

    for _ in range(max_retries):
        try:
            mysql_manager = MySQLManager()
            mysql_manager.connect()
            mysql_manager.disconnect()
            log("Successfully connected to MySQL")
            return
        except Exception as e:
            log(f"Failed to connect to MySQL: {e}", "error")
            time.sleep(retry_interval)

    raise Exception("Failed to connect to MySQL after multiple retries")

def create_app():
    wait_for_mysql()
    
    app = Flask(__name__)
    CORS(app)
    app.config['SECRET_KEY'] = 'your_secret_key'
    socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

    # Import routes after app is created to avoid circular imports
    from routes import register_routes
    register_routes(app)

    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
