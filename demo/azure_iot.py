#!/usr/bin/env python3
"""Routines to communicate with azure
"""

import json
import os
import asyncio
import argparse
from azure.iot.device.aio import IoTHubModuleClient


async def connect():
    """Connect to the hub."""
    module_client = IoTHubModuleClient.create_from_edge_environment(
        websockets=True
    )
    await module_client.connect()
    return module_client


async def get_twin():
    """Get the module twin"""
    module_client = await connect()
    twin_data = await module_client.get_twin()
    await module_client.disconnect()
    return twin_data


async def update_twin(new_data):
    """Update the module twin"""
    module_client = await connect()
    await module_client.patch_twin_reported_properties(new_data)
    await module_client.disconnect()


async def send_outputs(data: dict) -> dict:
    """Send outputs to the hub."""
    module_client = await connect()
    data["optraDeviceName"] = os.getenv("OPTRA_DEVICE_NAME")
    data["optraSerialNumber"] = os.getenv("OPTRA_SERIAL_NUMBER")
    message = {}
    message["data"] = data
    msg = json.dumps(message)
    await module_client.send_message_to_output(msg, "output1")
    await module_client.disconnect()
    return message


async def get():
    """Call get_twin() and print result."""
    twin = await get_twin()
    print(twin)


async def update(data):
    """Update the twin with the supplied data."""
    await update_twin(data)


async def send(data):
    """Send the supplied data to the hub."""
    jsondata = json.loads(data)
    sent = await send_outputs(jsondata)
    print("Sent:\n" + json.dumps(sent, indent=4))


if __name__ == '__main__':
    P = argparse.ArgumentParser(
        description='Perform azure iot device functions'
    )
    P.version = '1.0'

    P.add_argument('-v', '--version', action='version')

    subp = P.add_subparsers(required=True, dest='func')

    Pget = subp.add_parser('get', help='get module twin')
    Pget.set_defaults(func=get)

    Pupdate = subp.add_parser('update', help='update update module twin')
    Pupdate.add_argument('data')
    Pupdate.set_defaults(func=update)

    Psend = subp.add_parser('send', help='send outputs to hub')
    Psend.add_argument('data')
    Psend.set_defaults(func=send)

    args = P.parse_args()
    args_ = vars(args).copy()
    args_.pop('command', None)
    args_.pop('func', None)

    asyncio.run(args.func(**args_))
