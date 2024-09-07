import time, os
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from mysql_manager import MySQLManager
from shared_data import log, activity_queue, set_socketio
import json
import eventlet

eventlet.monkey_patch()

socketio = SocketIO(async_mode='eventlet', cors_allowed_origins="*")

def wait_for_mysql():
    mysql_manager = MySQLManager()
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            mysql_manager.connect()
            log("Successfully connected to MySQL database")
            return
        except Exception as e:
            log(f"Failed to connect to MySQL (attempt {attempt + 1}/{max_attempts}): {e}", "error")
            if attempt < max_attempts - 1:
                time.sleep(5)
    raise Exception("Failed to connect to MySQL after multiple attempts")

def create_app():
    app = Flask(__name__)

    # Set the secret key
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_fallback_secret_key_here')

    CORS(app)
    socketio.init_app(app, async_mode='eventlet', ping_timeout=10, ping_interval=5)
    set_socketio(socketio)  # Set the socketio instance in shared_data

    # Import routes after app is created to avoid circular imports
    from routes import register_routes
    register_routes(app)

    @socketio.on('connect', namespace='/crawler')
    def handle_connect():
        # Emit all existing log entries when a client connects
        while not activity_queue.empty():
            log_entry = activity_queue.get()
            socketio.emit('log_update', json.loads(log_entry), namespace='/crawler')

    def background_task():
        while True:
            if not activity_queue.empty():
                log_entry = activity_queue.get()
                log_data = json.loads(log_entry)
                if 'crawler_update' in log_data:
                    # This is a crawler update
                    socketio.emit('crawler_update', log_data['crawler_update'], namespace='/crawler')
                else:
                    # This is a regular log entry
                    socketio.emit('log_update', log_data, namespace='/crawler')
            eventlet.sleep(0.1)

    socketio.start_background_task(background_task)

    return app, socketio

if __name__ == '__main__':
    app, socketio = create_app()
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
