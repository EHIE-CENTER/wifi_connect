import asyncio
from collections import namedtuple
import logging
import os
import re

import aiofiles
from pbkdf2 import PBKDF2


_LOGGER = logging.getLogger(__name__)
Network = namedtuple('Network', ['ssid', 'encryption'])

networks_re = re.compile(r'Cell \d+ - ')
ssid_scan_re = re.compile("ESSID:\"(.*?)\"", re.M)
ssid_interface_re = re.compile("\\s+wpa-ssid\\s+\"(.*?)\"", re.M)
bound_ip_re = re.compile(r'^bound to (?P<ip_address>\S+)', flags=re.MULTILINE)

interface_file = '/etc/network/interfaces'


async def get_ip_address(interface):
    _LOGGER.debug("Getting IP address")
    cmd = asyncio.create_subprocess_exec('ip', 'addr', 'show', interface,
                                         stdout=asyncio.subprocess.PIPE,
                                         stderr=asyncio.subprocess.PIPE)
    proc = await cmd
    stdout_data, stderr_data = await proc.communicate()
    _LOGGER.debug("stdout: %s", stdout_data)
    _LOGGER.debug("stderr: %s", stderr_data)
    stdout_data = stdout_data.decode()

    if 'inet ' not in stdout_data:
        _LOGGER.debug("No IP address")
        return None
    else:
        ip_address = stdout_data.split('inet ')[1].split("/")[0]
        _LOGGER.debug("Found IP address: %s", ip_address)
        return ip_address


async def is_connected(interface):
    try:
        ip_address = await get_ip_address(interface)
        message = 'Connected ({})'.format(ip_address) \
                  if ip_address is not None else 'Not Connected'
    except Exception as e:
        _LOGGER.exception("Unable to determine if connected")
        message = 'Unknown'

    return message


async def get_ssid(interface):
    _LOGGER.debug("Getting SSID")
    filename = '{}.d/{}.cfg'.format(interface_file, interface)

    if not os.path.isfile(filename):
        _LOGGER.debug("Interface file for %s does not exist", interface)
        return None

    async with aiofiles.open(filename) as f:
        text = await f.read()
        match = ssid_interface_re.search(text)

        if match:
            _LOGGER.debug("Found SSID for interface: %s", match.group(1))
            return match.group(1)
        else:
            _LOGGER.debug("Could not find SSD for interface")
            return None


async def scan(interface):
    _LOGGER.debug("Scanning for wireless networks")
    cmd = asyncio.create_subprocess_exec('iwlist', interface, 'scan',
                                         stdout=asyncio.subprocess.PIPE,
                                         stderr=asyncio.subprocess.PIPE)
    proc = await cmd
    stdout_data, stderr_data = await proc.communicate()
    _LOGGER.debug("stdout: %s", stdout_data)
    _LOGGER.debug("stderr: %s", stderr_data)
    networks = stdout_data.decode()

    def create_network(network):
        ssid = ssid_scan_re.search(network).group(1)

        if 'Encryption key:on' in network:
            if 'WPA2' in network:
                encryption = 'wpa2'
            elif 'WPA' in network:
                encryption = 'wpa'
            else:
                # Encryption is on but not specified
                encryption = 'wep'
        else:
            encryption = None

        return Network(ssid, encryption)

    return (create_network(n) for n in networks_re.split(networks)[1:])


async def replace(interface, network, passkey):
    _LOGGER.debug("Setting new SSID and passkey")
    lines = ['auto {}\n'.format(interface),
             'iface {} inet dhcp\n'.format(interface)]

    if network.encryption.startswith('wpa'):
        if len(passkey) != 64:
            passkey = PBKDF2(passkey, network.ssid, 4096).hexread(32)

        lines.append('    wpa-ssid "{}"\n'.format(network.ssid))
        lines.append('    wpa-psk  "{}"\n'.format(passkey))

    elif network.encryption == 'wep':
        if len(passkey) in (5, 13, 16, 29):
            passkey = "s:" + passkey

        lines.append('    wireless-essid "{}"'.format(network.ssid))
        lines.append('    wireless-key   "{}"'.format(passkey))

    else:
        raise NotImplementedError

    filename = '{}.d/{}.cfg'.format(interface_file, interface)
    async with aiofiles.open(filename, 'w') as f:
        for line in lines:
            await f.write(line)


async def connect(interface):
    _LOGGER.debug("Connecting")

    _LOGGER.debug("Calling ifdown")
    cmd = asyncio.create_subprocess_exec('ifdown', interface,
                                         stdout=asyncio.subprocess.PIPE,
                                         stderr=asyncio.subprocess.PIPE)
    proc = await cmd
    stdout_data, stderr_data = await proc.communicate()
    _LOGGER.debug("stdout: %s", stdout_data)
    _LOGGER.debug("stderr: %s", stderr_data)

    _LOGGER.debug("Calling ifup")
    cmd = asyncio.create_subprocess_exec('ifup', interface,
                                         stdout=asyncio.subprocess.PIPE,
                                         stderr=asyncio.subprocess.PIPE)
    proc = await cmd
    stdout_data, stderr_data = await proc.communicate()
    _LOGGER.debug("stdout: %s", stdout_data)
    _LOGGER.debug("stderr: %s", stderr_data)
    output = stderr_data.decode()
    matches = bound_ip_re.search(output)
    if matches:
        _LOGGER.debug("Connected: %s", matches.group('ip_address'))
        return matches.group('ip_address')
    else:
        _LOGGER.debug("Not connected")
        return None


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
