from web_app import create_app
from shared_data import log

app, socketio = create_app()

if __name__ == "__main__":
    log("This file should not be run directly. Use Gunicorn to serve the application.")
