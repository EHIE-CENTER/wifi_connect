import asyncio
from collections import namedtuple
import logging

_LOGGER = logging.getLogger(__name__)
Network = namedtuple('Network',
                     ['ssid', 'encrypted', 'address', 'mode', 'channel', 'signal'])


async def get_ip_address(interface):
    try:
        cmd = asyncio.create_subprocess_exec('ip', 'addr', 'show', interface,
                                             stdout=asyncio.subprocess.PIPE)

        proc = await cmd
        stdout_data, stderr_data = await proc.communicate()
        return stdout_data.decode('ascii').split("inet ")[1].split("/")[0]

    except IndexError as e:
        return None


async def is_connected(interface):
    try:
        ip_address = await get_ip_address(interface)
        message = 'Connected ({})'.format(ip_address) \
                  if ip_address is not None else 'Not Connected'
    except Exception:
        message = 'Unknown'

    return message


async def get_ssid(interface):
    return "Art Vandelay"


async def scan(interface):
    return [Network('Network 1', False, '?', '?', 1, -43),
            Network('Network 2', False, '?', '?', 1, -28)]


async def replace(interface, ssid, password):
    pass

async def connect(interface, ssid):
    pass
