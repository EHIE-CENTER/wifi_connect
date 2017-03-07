from aiohttp import web
import logging
from logging import handlers

from server import app

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(threadName)s:%(levelname)s:'
                           '%(name)s:%(message)s',
                    handlers=[
                        logging.handlers.TimedRotatingFileHandler(
                            'prisms-wifi.log', when='midnight', backupCount=7,
                            delay=True),
                        logging.StreamHandler()])

web.run_app(app)
