import asyncio
from contextlib import contextmanager
import logging

import wifi

logging.basicConfig(level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)
CHANNELS = range(1, 12)
CONNECTED_WAIT_TIME = 5 * 60
RECEIVE_WAIT_TIME = 5
RUNNING = True


async def start(interface):
    _LOGGER.debug("Starting...")
    while RUNNING:
        if await connected(interface):
            _LOGGER.debug("Already connected. Waiting %s before checking again.",
                          CONNECTED_WAIT_TIME)
            await asyncio.sleep(CONNECTED_WAIT_TIME)
            continue

        _LOGGER.debug("Not connected")

        async with MonitorMode(interface) as monitor:
            for channel in CHANNELS:
                await monitor.set_channel(channel)

                wifi_info = await receive_wifi_info(interface)
                if wifi_info is not None:
                    await save_wifi_credentials(wifi_info)
                    break

        if await has_wifi_credentials(interface):
            await connect()


def stop():
    global RUNNING
    RUNNING = False


async def connect(interface):
    await wifi.connect(interface)


async def connected(interface):
    try:
        ip_address = await wifi.get_ip_address(interface)
        return ip_address is not None
    except Exception as e:
        _LOGGER.exception("Unable to determine if connected")
        return False


async def has_wifi_credentials(interface):
    return await inteface_configured(interface)


async def save_wifi_credentials(interface, ssid, password):
    await wifi.replace(interface, ssid, password)


async def receive_wifi_info(interface):
    # # TODO: Timeout!
    _LOGGER.debug("Receiving WiFi Info")
    cmd = asyncio.create_subprocess_exec(
        'echo', 'test:test',
        # '/usr/local/var/pyenv/versions/unassociated_transfer-2/bin/python',
        # '/Users/philipbl/Projects/unassociated_transfer/receive_wifi.py',
        # interface,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    proc = await cmd

    try:
        stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(),
                                                          RECEIVE_WAIT_TIME)
        _LOGGER.debug("stdout: %s", stdout_data)
        _LOGGER.debug("stderr: %s", stderr_data)

        data = stdout_data.decode()
        _LOGGER.debug("Received wifi info: %s", data)
        ssid, password = data.split(':')

        return ssid, password
    except asyncio.TimeoutError:
        _LOGGER.debug("Timing out receiving WiFi info")
        return None


class MonitorMode():
    def __init__(self, interface):
        self.interface = interface

    async def set_channel(self, channel):
        _LOGGER.debug("Setting channel to %s", channel)
        await asyncio.sleep(1)

    async def __aenter__(self):
        _LOGGER.debug("Entering monitor mode")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        _LOGGER.debug("Exiting monitor mode")


loop = asyncio.get_event_loop()
loop.run_until_complete(start('wlan0'))
