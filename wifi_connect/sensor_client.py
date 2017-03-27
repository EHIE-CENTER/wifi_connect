import asyncio
from collections import namedtuple
from contextlib import contextmanager
import logging

import wifi

logging.basicConfig(level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)
CHANNELS = range(1, 2)
CONNECTED_WAIT_TIME = 5 * 60
RECEIVE_WAIT_TIME = 30
RUNNING = True
Network = namedtuple('Network', ['ssid', 'encryption'])


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
                _LOGGER.debug("Setting channel to %s", channel)
                await monitor.set_channel(channel)

                wifi_info = await receive_wifi_info(interface)
                _LOGGER.debug("Received wifi info: %s", wifi_info)
                if wifi_info is not None:
                    ssid, password = wifi_info
                    _LOGGER.debug("Saving WiFi credentials")
                    await save_wifi_credentials(interface, ssid, password)
                    break

        if await has_wifi_credentials(interface):
            _LOGGER.debug("We have WiFi credentials, so we are trying to connect")
            await asyncio.sleep(5)
            # await connect()


def stop():
    global RUNNING
    RUNNING = False


async def connect(interface):
    # await wifi.connect(interface)
    pass


async def connected(interface):
    try:
        ip_address = await wifi.get_ip_address(interface)
        return ip_address is not None
    except Exception as e:
        _LOGGER.exception("Unable to determine if connected")
        return False


async def has_wifi_credentials(interface):
    return await wifi.interface_configured(interface)


async def save_wifi_credentials(interface, ssid, password):
    network = Network(ssid, 'wpa')
    await wifi.replace(interface, network, password)


async def receive_wifi_info(interface):
    _LOGGER.debug("Receiving WiFi Info")
    cmd = asyncio.create_subprocess_exec(
        '/usr/bin/python',
        '/root/unassociated_transfer/receive_wifi.py',
        interface,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    proc = await cmd

    try:
        stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(),
                                                          RECEIVE_WAIT_TIME)
        _LOGGER.debug("stdout: %s", stdout_data)
        _LOGGER.debug("stderr: %s", stderr_data)

        data = stdout_data.decode()
        ssid, password = data.strip().split(':')

        return ssid, password
    except asyncio.TimeoutError:
        _LOGGER.debug("Timing out receiving WiFi info")
        return None


class MonitorMode():
    def __init__(self, interface):
        self.interface = interface

    async def set_channel(self, channel):
        cmd = asyncio.create_subprocess_exec(
            'iwconfig', self.interface, 'channel', str(channel),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        proc = await cmd
        stdout_data, stderr_data = await proc.communicate()

        _LOGGER.debug("stdout: %s", stdout_data)
        _LOGGER.debug("stderr: %s", stderr_data)

    async def __aenter__(self):
        _LOGGER.debug("Entering monitor mode")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        _LOGGER.debug("Exiting monitor mode")
