# import monkey_patch  # This import is commented out as it's currently unused

from flask import Flask
from flask_socketio import SocketIO
from routes import register_routes


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your_secret_key'
    socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

    # Import routes after app is created to avoid circular imports
    register_routes(app)

    return app, socketio


if __name__ == '__main__':
    app, socketio = create_app()
    socketio.run(app, debug=True)
