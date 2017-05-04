import asyncio
import logging

from aiohttp import web
import socketio

# from send_wifi import main as send_wifi

import utils
import wifi


_LOGGER = logging.getLogger(__name__)
BROADCAST_WAIT_TIME = 2

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

broadcasting = False
sensor_queue = asyncio.Queue()


async def index(request):
    """Serve the client-side application."""
    with open('static/gateway-index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')


async def sensor_ping(request):
    if not broadcasting:
        return web.Response(text='Not broadcasting', content_type='text')
    data = await request.post()

    if 'sensor' not in data:
        return web.Response(text='Must have sensor field', content_type='text')

    sensor_queue.put_nowait(data['sensor'])
    return web.Response(text='Sensor has been added', content_type='text')


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

    if 'sensors' not in data or len(data['sensors']) == 0:
        await sio.emit('broadcast-update',
                       {'message': 'Number of sensors must be provided'},
                       room=sid)
        return

    if broadcasting:
        await sio.emit('broadcast-update',
                       {'message': 'Already broadcasting'},
                       room=sid)
        return

    ssid = data['ssid']
    password = data['password']
    expected_sensors = int(data['sensors'])
    broadcasting = True

    await sio.emit('broadcast-update',
                   {'message': 'Starting...'},
                   room=sid)
    await status(sid)

    asyncio.ensure_future(broadcast(ssid, password, expected_sensors, sid))


async def broadcast(ssid, password, expected_sensors, sid):
    global broadcasting
    found_sensors = set()
    # Something that keeps track of how long its beens sending and increases FEC

    send_flag = 0
    while broadcasting:
        await send_wifi_info(ssid, password, send_flag, .87)

        # Switch between 0 and 1
        send_flag = 1 - send_flag

        for i in range(BROADCAST_WAIT_TIME):
            _LOGGER.debug("Waiting (%s)...", i)
            if not broadcasting:
                break

            await check_for_sensors(expected_sensors, found_sensors, sid)
            await asyncio.sleep(1)

    await sio.emit('broadcast-update',
                   {'message': 'Stopped'},
                   room=sid)
    await status(sid)


async def send_wifi_info(ssid, password, send_flag, possible_loss):
    _LOGGER.debug("Sending WiFi information")
    # TODO: Generalize this
    cmd = asyncio.create_subprocess_exec(
        'python',
        '/home/pi/unassociated_transfer/send_wifi.py',
        '-l', str(possible_loss),
        '-s', str(send_flag),
        ssid, password,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    proc = await cmd
    stdout_data, stderr_data = await proc.communicate()
    _LOGGER.debug("stdout: %s", stdout_data)
    _LOGGER.debug("stderr: %s", stderr_data)
    _LOGGER.debug("-" * 80)
    _LOGGER.debug("Done sending WiFi information")


async def check_for_sensors(expected_sensors, found_sensors, sid):
    global broadcasting

    try:
        found_sensors.add(sensor_queue.get_nowait())
        _LOGGER.debug("sensors discovered: %s", found_sensors)
        await sio.emit('broadcast-update',
                       {'message': 'Starting... (Discovered sensors: {})'.format(found_sensors)},
                       room=sid)

        if len(found_sensors) >= expected_sensors:
            _LOGGER.debug("Discovered all sensors so stopping")
            broadcasting = False
    except asyncio.QueueEmpty:
        pass


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
app.router.add_post('/ping', sensor_ping)
