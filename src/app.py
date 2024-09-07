from web_app import create_app
from shared_data import log
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import socket


def find_free_port(start_port=8080, max_port=9000):
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    raise OSError("No free ports available")


if __name__ == "__main__":
    app, socketio = create_app()
    port = find_free_port()
    log(f"Starting server on port {port}")
    server = pywsgi.WSGIServer(
        ('0.0.0.0', port),
        app,
        handler_class=WebSocketHandler
    )
    server.serve_forever()
