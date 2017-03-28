import argparse
import asyncio
import functools
import logging
from logging import handlers
import signal

from aiohttp import web

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(threadName)s:%(levelname)s:'
                           '%(name)s:%(message)s',
                    handlers=[
                        handlers.TimedRotatingFileHandler(
                            'prisms-wifi.log', when='midnight', backupCount=7,
                            delay=True),
                        logging.StreamHandler()])


def ask_exit(signame):
    print("got signal %s: exit" % signame)
    loop.stop()

# Set up the loop
loop = asyncio.get_event_loop()
# for signame in ('SIGINT', 'SIGTERM'):
#     loop.add_signal_handler(getattr(signal, signame),
#                             functools.partial(ask_exit, signame))


def run_gateway(args):
    from gateway_server import app
    web.run_app(app, port=3210)


def run_sensor(args):
    import wifi
    import sensor_client
    from sensor_server import app

    app.interface = args.interface

    # Make sure interface file is configured correctly
    loop.run_until_complete(wifi.update_interfaces())

    # Start process to listen for gateway broadcasts
    asyncio.ensure_future(sensor_client.start(args.interface))

    # Start server
    web.run_app(app, port=3210)


parser = argparse.ArgumentParser(
    description='Application to help sensors connect to WiFi')
subparsers = parser.add_subparsers(help='Which device to run application on',
                                   dest='type')
subparsers.required = True

parser_sensor = subparsers.add_parser('sensor')
parser_sensor.add_argument('interface', help='Wireless interface to use')
parser_sensor.set_defaults(func=run_sensor)

parser_gateway = subparsers.add_parser('gateway')
parser_gateway.set_defaults(func=run_gateway)

args = parser.parse_args()
args.func(args)
