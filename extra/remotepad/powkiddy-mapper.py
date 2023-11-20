#!/usr/bin/env -S python3 -u

PROTOCOL_VERSION = '2'

import argparse
import asyncio
import evdev
import json

from evdev import ecodes, categorize, AbsInfo

async def do_forward_device(device, options):
	async for event in device.async_read_loop():
		if options['map_dpad_x_to_hat'] and event.type == ecodes.EV_KEY and event.code == ecodes.BTN_DPAD_LEFT:
			print(json.dumps([0, ecodes.EV_ABS, ecodes.ABS_HAT0X, [0, -1][event.value]]))
		elif options['map_dpad_x_to_hat'] and event.type == ecodes.EV_KEY and event.code == ecodes.BTN_DPAD_RIGHT:
			print(json.dumps([0, ecodes.EV_ABS, ecodes.ABS_HAT0X, [0,  1][event.value]]))
		elif options['map_dpad_y_to_hat'] and event.type == ecodes.EV_KEY and event.code == ecodes.BTN_DPAD_UP:
			print(json.dumps([0, ecodes.EV_ABS, ecodes.ABS_HAT0Y, [0, -1][event.value]]))
		elif options['map_dpad_y_to_hat'] and event.type == ecodes.EV_KEY and event.code == ecodes.BTN_DPAD_DOWN:
			print(json.dumps([0, ecodes.EV_ABS, ecodes.ABS_HAT0Y, [0,  1][event.value]]))
		else:
			print(json.dumps([0, event.type, event.code, event.value]))

async def forward_device(device, options):
	if args.exclusive:
		with device.grab_context():
			await do_forward_device(device, options)
	else:
		await do_forward_device(device, options)

def merge_capabilities(devices):
	merged = {}

	for device in devices:
		for etype, caps in device.capabilities().items():
			if etype is ecodes.EV_SYN:
				continue

			elif etype is ecodes.EV_KEY:
				if etype not in merged:
					merged[etype] = []

				for key in caps:
					if key in merged[etype]:
						raise ValueError("KEY %d already merged" % (key))
					merged[etype].append(key)

			elif etype is ecodes.EV_ABS:
				if etype not in merged:
					merged[etype] = []
				
				for abs in caps:
					# todo: check for duplicates
					merged[etype].append([abs[0], abs[1]._asdict()])

			else:
				raise ValueError("unexpected cap etype: %s" % (etype))
				print(etype, caps)

	return merged

async def run_forward():
	# Find devices
	devices_by_name = {}
	if args.device_by_name:
		for path in evdev.list_devices():
			device = evdev.InputDevice(path)
			devices_by_name[device.name] = device
	
	devices = []
	for path in args.device_by_path:
		devices.append(evdev.InputDevice(path))
	for name in args.device_by_name:
		devices.append(devices_by_name[name])


	# Merge and remap capabilities
	capabilities = merge_capabilities(devices)

	map_dpad_x_to_hat = False
	if ecodes.EV_KEY in capabilities:
		if ecodes.BTN_DPAD_LEFT in capabilities[ecodes.EV_KEY]:
			if ecodes.BTN_DPAD_RIGHT in capabilities[ecodes.EV_KEY]:
				capabilities[ecodes.EV_KEY].remove(ecodes.BTN_DPAD_LEFT)
				capabilities[ecodes.EV_KEY].remove(ecodes.BTN_DPAD_RIGHT)
				map_dpad_x_to_hat = True

	map_dpad_y_to_hat = False
	if ecodes.EV_KEY in capabilities:
		if ecodes.BTN_DPAD_UP in capabilities[ecodes.EV_KEY]:
			if ecodes.BTN_DPAD_DOWN in capabilities[ecodes.EV_KEY]:
				capabilities[ecodes.EV_KEY].remove(ecodes.BTN_DPAD_UP)
				capabilities[ecodes.EV_KEY].remove(ecodes.BTN_DPAD_DOWN)
				map_dpad_y_to_hat = True

	if map_dpad_x_to_hat or map_dpad_y_to_hat:
		if ecodes.EV_ABS not in capabilities:
			capabilities[ecodes.EV_ABS] = []

		if map_dpad_x_to_hat:
			capabilities[ecodes.EV_ABS].append((
				ecodes.ABS_HAT0X,
				evdev.AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)._asdict()
			))

		if map_dpad_y_to_hat:
			capabilities[ecodes.EV_ABS].append((
				ecodes.ABS_HAT0Y,
				evdev.AbsInfo(value=0, min=-1, max=1, fuzz=0, flat=0, resolution=0)._asdict()
			))

	options = {
		'map_dpad_x_to_hat': map_dpad_x_to_hat,
		'map_dpad_y_to_hat': map_dpad_y_to_hat
	}

	# Report version
	print(PROTOCOL_VERSION)

	print(json.dumps([{
		'name': 'Powkiddy X55',
		'capabilities': capabilities,
		'vendor': 0,
		'product': 0
	}]))

	tasks = []
	for i, device in enumerate(devices):
		tasks.append(asyncio.create_task(forward_device(device, options)))
	
	await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

async def list_devices():
	for path in evdev.list_devices():
		device = evdev.InputDevice(path)
		print('{}  {}'.format(device.path, device.name))

parser = argparse.ArgumentParser(description='input-over-ssh client')
parser.add_argument('-L', '--list-devices', dest='action', action='store_const', const=list_devices, help='List available input devices')
parser.add_argument('-p', '--device-by-path', action='append', default=[], help='Forward device with the given path')
parser.add_argument('-n', '--device-by-name', action='append', default=[], help='Forward device with the given name')
parser.add_argument('-e', '--exclusive', action='store_true', help='Grab the device for exclusive input')
args = parser.parse_args()

if not args.action:
	args.action = run_forward

try:
	asyncio.run(args.action())
except KeyboardInterrupt:
	pass
