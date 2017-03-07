import asyncio
import logging

from aiohttp import web
import socketio

import utils
import wifi


_LOGGER = logging.getLogger(__name__)
INTERFACE = 'ra0'


sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

app.router.add_static('/', 'static')


@sio.on('wifi-status')
async def handle_wifi_status(sid):
    message = await wifi.is_connected(INTERFACE)
    await sio.emit('wifi-status', {'message': message})


@sio.on('wifi-get')
async def handle_wifi_get(sid):
    ssid = await wifi.get_ssid(INTERFACE)

    if ssid is None:
        await sio.emit('wifi-get', {'ssid': ''})
    else:
        await sio.emit('wifi-get', {'ssid': ssid})


@sio.on('wifi-scan')
async def handle_wifi_scan(sid):
    networks = await wifi.scan(INTERFACE)
    networks = sorted(networks, key=lambda x: x.lower())

    await sio.emit('wifi-scan', networks)


@sio.on('wifi-update')
async def handle_wifi_update(sid, data):
    if 'ssid' not in data or len(data['ssid']) == 0:
        await sio.emit('wifi-update', {'message': 'Network name must be provided'})
        return

    if 'password' not in data or len(data['password']) == 0:
        await sio.emit('wifi-update', {'message': 'Password must be provided'})
        return

    ssid = data['ssid']
    password = data['password']

    await sio.emit('wifi-update', {'message': 'Looking for network...'})
    networks = await wifi.scan(INTERFACE)
    await asyncio.sleep(.2)
    if ssid not in (n.ssid for n in networks):
        await sio.emit('wifi-update', {'message': 'No network named {}'.format(ssid)})
        return

    await sio.emit('wifi-update', {'message': 'Saving network name and password...'})
    await wifi.replace(INTERFACE, ssid, password)
    await asyncio.sleep(.2)

    await sio.emit('wifi-status', {'message': 'Not Connected'})
    await sio.emit('wifi-update', {'message': 'Connecting...'})
    await asyncio.sleep(.2)

    ip_address = await wifi.connect(INTERFACE, ssid)
    await sio.emit('wifi-update', {'message': 'Connected!'})
    await handle_wifi_status(None)

    result = await utils.restart_sensor_service()
    if not result:
        await sio.emit('wifi-update',
                       {'message': 'Connected! An error occurred while '
                                   'restarting sensor service. Please restart'
                                   ' device.'})
