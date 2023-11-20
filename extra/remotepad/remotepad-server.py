#!/usr/bin/env python3

#   input-over-ssh: Forwarding arbitrary input devices over SSH
#   Copyright © 2019  Lee Yingtong Li (RunasSudo)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

PROTOCOL_VERSION = '2'

import evdev
import json

from evdev import ecodes, categorize, AbsInfo

version = input()
if version != PROTOCOL_VERSION:
	raise Exception('Invalid protocol version. Got {}, expected {}.'.format(version, PROTOCOL_VERSION))

devices_json = json.loads(input())
devices = []

for device_json in devices_json:
	capabilities = {}
	for etype, caps in device_json['capabilities'].items():
		etype = int(etype)

		if etype is ecodes.EV_KEY:
			capabilities[etype] = caps
		elif etype is ecodes.EV_ABS:
			abses = []
			for cap in caps:
				# that's fukin krazy
				if cap[1]['min'] > cap[1]['max']:
					cap[1]['min'], cap[1]['max'] = cap[1]['max'], cap[1]['min']
				abses.append((cap[0], evdev.AbsInfo(**cap[1])))
			capabilities[etype] = abses
		else:
			raise ValueError("unexpected cap etype: %s" % (etype))

	device = evdev.UInput(capabilities, name=device_json['name'], vendor=device_json['vendor'], product=device_json['product'])
	devices.append(device)

print('Device created')

while True:
	event = json.loads(input())
	#print(event)
	devices[event[0]].write(event[1], event[2], event[3])
