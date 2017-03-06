import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


async def restart_sensor_service():
    try:
        cmd = asyncio.create_subprocess_exec('systemctl', 'restart', 'sensor.service')
        proc = await cmd
        await proc.wait()
        return True
    except Exception as e:
        _LOGGER.exception("Failed to restart service: %s", e)
        return False
