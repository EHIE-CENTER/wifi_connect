import time

from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


@app.route("/", methods=['GET'])
def main():
    return render_template('setup.html')


@socketio.on('wifi-status')
def handle_wifi_status():
    # TODO: Go get Wifi status
    emit('wifi-status', {'message': 'Connected'})


@socketio.on('wifi-get')
def handle_wifi_get():
    # TODO: Go get WiFi parameters
    emit('wifi-get', {'ssid': 'Art Vandelay', 'password': '11009178'})


@socketio.on('wifi-scan')
def handle_wifi_scan():
    # TODO: Scan WiFi
    data = ['Art Vandelay', 'BakerGirl']
    emit('wifi-scan', data)


@socketio.on('wifi-update')
def handle_wifi_update(data):
    if 'ssid' not in data or 'password' not in data:
        emit('wifi-update', {'message': 'Invalid request to wifi-update'})

    emit('wifi-update', {'message': 'Updating...'})
    # TODO: update WiFi

    # Update the status of WiFi
    handle_wifi_status()


if __name__ == "__main__":
    socketio.run(app, port=3210, debug=True)
