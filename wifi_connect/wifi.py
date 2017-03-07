import asyncio
from collections import namedtuple
import logging
import os
import re
import textwrap

import aiofiles


_LOGGER = logging.getLogger(__name__)
Network = namedtuple('Network',
                     ['ssid', 'encrypted', 'address', 'mode', 'channel', 'signal'])
ssid_scan_re = re.compile("ESSID:\"(.*?)\"", re.M)
ssid_interface_re = re.compile("\\s+wpa-ssid\\s+\"(.*?)\"", re.M)
bound_ip_re = re.compile(r'^bound to (?P<ip_address>\S+)', flags=re.MULTILINE)

interface_file = 'etc/network/interfaces'


async def get_ip_address(interface):
    cmd = asyncio.create_subprocess_exec('ip', 'addr', 'show', interface,
                                         stdout=asyncio.subprocess.PIPE)
    proc = await cmd
    stdout_data, stderr_data = await proc.communicate()
    stdout_data = stdout_data.decode()

    if 'inet ' not in stdout_data:
        return None
    else:
        return stdout_data.split('inet ')[1].split("/")[0]


async def is_connected(interface):
    try:
        ip_address = await get_ip_address(interface)
        message = 'Connected ({})'.format(ip_address) \
                  if ip_address is not None else 'Not Connected'
    except Exception as e:
        message = 'Unknown'

    return message


async def get_ssid(interface):
    filename = '{}.d/{}.cfg'.format(interface_file, interface)

    if not os.path.isfile(filename):
        return None

    async with aiofiles.open(filename) as f:
        text = await f.read()
        match = ssid_interface_re.search(text)

        if match:
            return match.group(1)
        else:
            return None


async def scan(interface):
    cmd = asyncio.create_subprocess_exec('iwlist', interface, 'scan',
                                         stdout=asyncio.subprocess.PIPE)
    stdout_data, stderr_data = await proc.communicate()
    networks = stdout_data.decode()
    return (m.group(1) for m in ssid_scan_re.finditer(networks))


async def replace(interface, ssid, password):
    filename = '{}.d/{}.cfg'.format(interface_file, interface)
    async with aiofiles.open(filename, 'w') as f:
        await f.write('auto {}\n'.format(interface))
        await f.write('iface {} inet dhcp\n'.format(interface))
        await f.write('    wpa-ssid "{}"\n'.format(ssid))
        await f.write('    wpa-psk  "{}"\n'.format(password))


async def connect(interface):
    cmd = asyncio.create_subprocess_exec('ifdown', interface)
    proc = await cmd
    await proc.wait()

    cmd = asyncio.create_subprocess_exec('ifup', interface,
                                         stdout=asyncio.subprocess.PIPE)
    proc = await cmd
    stdout_data, stderr_data = await proc.communicate()
    result = stdout_data.decode()
    matches = bound_ip_re.search(output)
    if matches:
        return matches.group('ip_address')
    else:
        raise ConnectionError("Failed to connect to %r" % self)


async def update_interfaces():
    # Create the folder if necessary
    folder = '{}.d'.format(interface_file)
    if not os.path.exists(folder):
        _LOGGER.debug("%s does not exist. Creating it...")
        os.makedirs(folder)

    # Make sure the folder is included in the configuration
    config_line = 'source {}.d/*.cfg'.format(interface_file)

    if os.path.exists(interface_file):
        async with aiofiles.open(interface_file, 'r') as f:
            lines = await f.readlines()
            for line in lines:
                if line.strip().startswith('#'):
                    continue

                if config_line in line:
                    _LOGGER.debug("Found line in interface file")
                    return

    async with aiofiles.open(interface_file, 'a+') as f:
        await f.write('\n{}\n'.format(config_line))
        _LOGGER.debug("Adding line to interface file")


