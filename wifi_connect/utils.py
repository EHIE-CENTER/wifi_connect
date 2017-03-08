import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


async def restart_sensor_service():
    try:
        cmd = asyncio.create_subprocess_exec('systemctl',
                                             'restart',
                                             'sensor.service',
                                             stdout=asyncio.subprocess.PIPE,
                                             stderr=asyncio.subprocess.PIPE)
        proc = await cmd
        stdout_data, stderr_data = await proc.communicate()
        _LOGGER.debug("stdout: %s", stdout_data)
        _LOGGER.debug("stderr: %s", stderr_data)
        return True
    except Exception as e:
        _LOGGER.exception("Failed to restart service: %s", e)
        return False
