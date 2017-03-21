import asyncio
import logging

from aiohttp import web
import socketio

from send_wifi import main as send_wifi

import utils
import wifi


_LOGGER = logging.getLogger(__name__)

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

broadcasting = False


async def index(request):
    """Serve the client-side application."""
    with open('static/gateway-index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


@sio.on('broadcast-start')
async def start_broadcast(sid, data):
    global broadcasting

    if 'ssid' not in data or len(data['ssid']) == 0:
        await sio.emit('wifi-update',
                       {'message': 'Network name must be provided'})
        return

    if 'password' not in data or len(data['password']) == 0:
        await sio.emit('wifi-update', {'message': 'Password must be provided'})
        return

    ssid = data['ssid']
    password = data['password']
    broadcasting = True

    while broadcasting:
        # TODO: Run in thread
        send_wifi(ssid, password)


@sio.on('broadcast-start')
async def stop_broadcast(sid, data):
    broadcasting = False
    await sio.emit('wifi-update', {'message': 'Stopping'})


app.router.add_static('/static', 'static')
app.router.add_get('/', index)
