import asyncio
import logging

from aiohttp import web
import socketio

# from send_wifi import main as send_wifi

import utils
import wifi


_LOGGER = logging.getLogger(__name__)

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

broadcasting = False
pool = ThreadPoolExecutor(max_workers=1)


async def index(request):
    """Serve the client-side application."""
    with open('static/gateway-index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')

@sio.on('status')
async def status(sid):
    text = 'Broadcasting' if broadcasting else 'Not broadcasting'
    await sio.emit('status',
                   {'message': text},
                   room=sid)

@sio.on('broadcast-start')
async def start_broadcast(sid, data):
    global broadcasting

    if 'ssid' not in data or len(data['ssid']) == 0:
        await sio.emit('broadcast-update',
                       {'message': 'Network name must be provided'},
                       room=sid)
        return

    if 'password' not in data or len(data['password']) == 0:
        await sio.emit('broadcast-update',
                       {'message': 'Password must be provided'},
                       room=sid)
        return

    if broadcasting:
        await sio.emit('broadcast-update',
                       {'message': 'Already broadcasting'},
                       room=sid)
        return

    ssid = data['ssid']
    password = data['password']
    broadcasting = True

    await sio.emit('broadcast-update',
                   {'message': 'Starting...'},
                   room=sid)
    await status(sid)

    async def broadcast():
        await send_wifi_info(ssid, password)
        await sio.emit('broadcast-update',
                       {'message': 'Stopped'},
                       room=sid)

    asyncio.ensure_future(broadcast())


async def send_wifi_info(ssid, password):
    send_flag = 0

    while broadcasting:
        _LOGGER.debug("Sending WiFi information")
        # TODO: Generalize this
        cmd = asyncio.create_subprocess_exec(
            'python',
            '/home/pi/unassociated_transfer/send_wifi.py',
            '-l', '.6',
            '-s', send_flag,
            ssid, password,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        proc = await cmd
        stdout_data, stderr_data = await proc.communicate()
        _LOGGER.debug("stdout: %s", stdout_data)
        _LOGGER.debug("stderr: %s", stderr_data)
        _LOGGER.debug("-" * 80)
        _LOGGER.debug("Done sending WiFi information")

        # Switch between 0 and 1
        send_flag = 1 - send_flag

        _LOGGER.debug("Waiting...")
        await asyncio.sleep(15)


@sio.on('broadcast-stop')
async def stop_broadcast(sid):
    global broadcasting

    if not broadcasting:
        return

    broadcasting = False
    await sio.emit('broadcast-update',
                   {'message': 'Stopping...'},
                   room=sid)
    await status(sid)


app.router.add_static('/static', 'static')
app.router.add_get('/', index)
