import subprocess
import time

from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit
from wifi import Cell, Scheme

INTERFACE = 'ra0'
SCHEME = 'prisms'

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
    try:
        output = subprocess.check_output(['iwconfig', INTERFACE], stderr=subprocess.STDOUT)
    except CalledProcessError as e:
        print(e)
        emit('wifi-status', {'message': 'Error checking status'})
        return

    output = output.decode().split('\n')
    output = [o for o in output if 'Access Point' in o]
    connected = all(['Not-Associated' not in o for o in output])
    emit('wifi-status', {'message': 'Connected' if connected else 'Not Connected'})


@socketio.on('wifi-get')
def handle_wifi_get():
    scheme = Scheme.find(INTERFACE, SCHEME)

    if scheme is None:
        emit('wifi-get', {'ssid': ''})
    else:
        emit('wifi-get', {'ssid': scheme.options['wpa-ssid']})


@socketio.on('wifi-scan')
def handle_wifi_scan():
    networks = Cell.all(INTERFACE)
    networks = ((n.ssid, n.signal) for n in networks)
    networks = sorted(networks, key=lambda x: x[0].lower())

    emit('wifi-scan', networks)


@socketio.on('wifi-update')
def handle_wifi_update(data):
    if 'ssid' not in data or 'password' not in data:
        emit('wifi-update', {'message': 'Invalid request to wifi-update'})

    emit('wifi-update', {'message': 'Updating...'})
    # TODO: update WiFi

    # Update the status of WiFi
    handle_wifi_status()


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=3210, debug=True)

