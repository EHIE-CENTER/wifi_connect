import logging
from logging import handlers
from multiprocessing import Process, Queue
from queue import Empty
import time

from eventlet import greenthread
from eventlet.green import subprocess
import eventlet
eventlet.monkey_patch()
from flask import Flask, jsonify, render_template, send_from_directory, request, copy_current_request_context
from flask_socketio import SocketIO, emit
from wifi import Cell, Scheme

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(threadName)s:%(levelname)s:'
                           '%(name)s:%(message)s',
                    handlers=[
                        logging.handlers.TimedRotatingFileHandler(
                            'prisms-wifi.log', when='midnight', backupCount=7,
                            delay=True),
                        logging.StreamHandler()])

_LOGGER = logging.getLogger(__name__)
INTERFACE = 'ra0'
SCHEME = 'prisms'

app = Flask(__name__)
socketio = SocketIO(app, logger=True, engineio_logger=True)
queue = Queue()


def restart_sensor_service():
    try:
        output = subprocess.check_output(['systemctl', 'restart', 'sensor.service'])
        _LOGGER.info("Restarted service: %s", output)
    except subprocess.CalledProcessError as e:
        _LOGGER.exception("Failed to restart service: %s", e)


def get_ip_address():
    try:
        output = subprocess.check_output(['ip', 'addr', 'show', INTERFACE])
        output = output.decode().split("inet ")[1].split("/")[0]
        return output
    except IndexError as e:
        return None


@app.route('/js/<path:path>')
def send_js(path):
    return send_from_directory('js', path)


@app.route("/", methods=['GET'])
def main():
    return render_template('setup.html')


@socketio.on('wifi-status')
def handle_wifi_status():
    ip_address = get_ip_address()

    if ip_address is not None:
        emit('wifi-status', {'message': 'Connected ({})'.format(ip_address)})
    else:
        emit('wifi-status', {'message': 'Not Connected'})


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
    if 'ssid' not in data or len(data['ssid']) == 0:
        emit('wifi-update', {'message': 'Network name must be provided'})
        return

    if 'password' not in data or len(data['password']) == 0:
        emit('wifi-update', {'message': 'Password must be provided'})
        return

    ssid = data['ssid']
    password = data['password']

    # Find a network with this name
    emit('wifi-update', {'message': 'Looking for network...'})
    eventlet.sleep(.2)
    cells = Cell.where(INTERFACE, lambda x: x.ssid == ssid)

    if len(cells) == 0:
        emit('wifi-update', {'message': 'No network named {}'.format(ssid)})
        return

    emit('wifi-update', {'message': 'Saving network name and password...'})
    eventlet.sleep(.2)
    scheme = Scheme.for_cell(INTERFACE, SCHEME, cells[0], password)
    scheme.delete()
    scheme.save()

    emit('wifi-status', {'message': 'Not Connected'})
    emit('wifi-update', {'message': 'Connecting...'})
    eventlet.sleep(.2)

    def activate():
        try:
            result = scheme.activate()
            queue.put(('wifi-update', {'message': 'Connected!'}))
            queue.put(('wifi-status',
                       {'message': 'Connected ({})'.format(result.ip_address)}))

            restart_sensor_service()
        except Exception as e:
            _LOGGER.exception("Exception occurred: %s", e)
            queue.put(('wifi-update',
                       {'message': 'Unable to connect to network. Make sure '
                                   'password is correct.'}))

    p = Process(target=activate)
    p.start()


def check_processes():
    while True:
        try:
            name, data = queue.get_nowait()
            _LOGGER.debug("Emitting %s %s", name, data)
            socketio.emit(name, data)
        except Empty:
            eventlet.sleep(1)


if __name__ == "__main__":
    ip_address = get_ip_address()

    if ip_address is not None:
        _LOGGER.info("Network already connected")
    else:
        _LOGGER.info("Connecting to old network")
        scheme = Scheme.find(INTERFACE, SCHEME)
        if scheme is not None:
            try:
                scheme.activate()
            except Exception as e:
                _LOGGER.exception("Exception while connecting: %s", e)

        restart_sensor_service()

    _LOGGER.info("Starting web service")
    eventlet.spawn_n(check_processes)
    socketio.run(app, host='0.0.0.0', port=3210)
