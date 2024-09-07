from web_app import create_app
import eventlet

eventlet.monkey_patch()
app, socketio = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)
