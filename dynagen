#!/usr/bin/env python

"""
dynagen
Copyright (C) 2006  Greg Anuzelli

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import sys, os, re, traceback
from console import Console
from dynamips_lib import Dynamips, PA_C7200_IO_FE, PA_A1, PA_FE_TX, PA_4T, PA_8T, \
    PA_4E, PA_8E, PA_POS_OC3, Router, C7200, C3600, Leopard_2FE, NM_1FE_TX, NM_1E, NM_4E, \
    NM_16ESW, NM_4T, DynamipsError, DynamipsWarning, Bridge, FRSW, ATMSW, ETHSW, \
    NIO_udp, NIO_linux_eth, NIO_gen_eth, NIO_tap, NIO_unix, NIO_vde, nosend, setdebug, \
    IDLEPROPGET, IDLEPROPSHOW, IDLEPROPSET, C2691, C3725, C3745, GT96100_FE
from validate import Validator
from configobj import ConfigObj, flatten_errors
from optparse import OptionParser

# Constants
VERSION = '0.8.2.112806'
CONFIGSPECPATH = [ "/usr/share/dynagen", "/usr/local/share" ]
CONFIGSPEC = 'configspec'
INIPATH = [ "/etc", "/usr/local/etc" ]
INIFILE = 'dynagen.ini'
MODELTUPLE = (C2691, C3725, C3745, C3600, C7200)             # A tuple of known model objects
DEVICETUPLE = ('2691', '3725', '3745', '3620', '3640', '3660', '7200')  # A tuple of known device names

# Globals
debuglevel = 0     # The debug level
globaludp = 10000   # The default base UDP port for NIO
useridledbfile = '' # The filespec of the idle database
useridledb = None   # Dictionary of idle-pc values from the user database, indexed by image name
handled = False     # An exception has been handled already
globalconfig = {}   # A global copy of the config that console.py can access
configurations = {} # A global copy of all b64 exported configurations from the network file indexed by devicename
ghosteddevices = {} # A dict of devices that will use ghosted IOS indexed by device name
ghostsizes = {}     # A dict of the sizes of the ghosts
dynamips = {}       # A dictionary of dynamips objects, indexed by dynamips server name
devices = {}        # Dictionary of device objects, indexed by name
bridges = {}        # Dictionary of bridge objects, indexed by name
autostart = {}      # Dictionary that tracks autostart, indexed by router name
interface_re = re.compile(r"""^(f|fa|a|at|s|se|e|et|p|po)([0-9]+)\/([0-9]+)$""",  re.IGNORECASE)     # Regex matching intefaces
number_re = re.compile(r"""^[0-9]*$""")                         # Regex matching numbers
mapint_re = re.compile(r"""^([0-9]*):([0-9]*)$""")              # Regex matching Frame Relay mappings or ATM vpi mappings
mapvci_re = re.compile(r"""^([0-9]*):([0-9]*):([0-9]*)$""")     # Regex matching ATM vci mappings
ethswint_re = re.compile(r"""^([0-9]+)""")                      # Regex mating a number (means an Ethernet switchport config)

# determine if we are in the debugger
try:
    DBGPHideChildren
except NameError:
    DEBUGGER = False
else:
    DEBUGGER = True

def setdefaults(router, defaults):
    """ Apply the global defaults to this router instance
    """
    for option in defaults:
        setproperty(router, option, defaults[option])

def setproperty(device, option, value):
    """ If it is valid, set the option and return True. Otherwise return False
    """

    global configurations, ghosteddevices, globalconfig

    if type(device) in MODELTUPLE:
        # Is it a "simple" property? If so set it and forget it.
        if option in ('rom', 'clock', 'npe', 'ram', 'nvram', 'confreg', 'midplane', 'console', 'aux', 'mmap', 'idlepc', 'exec_area', 'disk0', 'disk1', 'iomem', 'idlemax', 'idlesleep'):
            setattr(device, option, value)
            return True
        # Is it a filespec? If so encase it in quotes to protect spaces
        if option in ('image', 'cnfg'):
            value = '"' + value + '"'
            setattr(device, option, value)
            return True

        # Is it a config? If so save it for later
        if option == 'configuration':
            configurations[device.name] = value

        if option == 'ghostios':
            ghosteddevices[device.name] = value

        if option == 'ghostsize':
            ghostsizes[device.name] = value

        # is it a slot designation?
        if type(device) == C7200:
            if option in ('slot0', 'slot1', 'slot2', 'slot3', 'slot4', 'slot5', 'slot6', 'slot7'):
                slot = int(option[4])
                if value == 'PA-C7200-IO-FE':
                    device.slot[slot] = PA_C7200_IO_FE(device, slot)
                elif value == 'PA-FE-TX':
                    device.slot[slot] = PA_FE_TX(device, slot)
                elif value == 'PA-A1':
                    device.slot[slot] = PA_A1(device, slot)
                elif value == 'PA-4T':
                    device.slot[slot] = PA_4T(device, slot)
                elif value == 'PA-8T':
                    device.slot[slot] = PA_8T(device, slot)
                elif value == 'PA-4E':
                    device.slot[slot] = PA_4E(device, slot)
                elif value == 'PA-8E':
                    device.slot[slot] = PA_8E(device, slot)
                elif value == 'PA-POS-OC3':
                    device.slot[slot] = PA_POS_OC3(device, slot)
                else:
                    return False
                return True
        elif type(device) == C3600:
            if device.chassis == '3620':
                if option in ('slot0', 'slot1'):
                    slot = int(option[4])
                    if value == 'NM-1FE-TX':
                        device.slot[slot] = NM_1FE_TX(device, slot)
                    elif value == 'NM-1E':
                        device.slot[slot] = NM_1E(device, slot)
                    elif value == 'NM-4E':
                        device.slot[slot] = NM_4E(device, slot)
                    elif value == 'NM-4T':
                        device.slot[slot] = NM_4T(device, slot)
                    elif value == 'NM-16ESW':
                        device.slot[slot] = NM_16ESW(device, slot)
                    else:
                        return False
                    return True
            elif device.chassis == '3640':
                if option in ('slot0', 'slot1', 'slot2', 'slot3'):
                    slot = int(option[4])
                    if value == 'NM-1FE-TX':
                        device.slot[slot] = NM_1FE_TX(device, slot)
                    elif value == 'NM-1E':
                        device.slot[slot] = NM_1E(device, slot)
                    elif value == 'NM-4E':
                        device.slot[slot] = NM_4E(device, slot)
                    elif value == 'NM-4T':
                        device.slot[slot] = NM_4T(device, slot)
                    elif value == 'NM-16ESW':
                        device.slot[slot] = NM_16ESW(device, slot)
                    else:
                        return False
                    return True
            elif device.chassis == '3660':
                if option in ('slot0', 'slot1', 'slot2', 'slot3', 'slot4', 'slot5', 'slot6'):
                    slot = int(option[4])
                    if value == 'NM-1FE-TX':
                        device.slot[slot] = NM_1FE_TX(device, slot)
                    elif value == 'NM-1E':
                        device.slot[slot] = NM_1E(device, slot)
                    elif value == 'NM-4E':
                        device.slot[slot] = NM_4E(device, slot)
                    elif value == 'NM-4T':
                        device.slot[slot] = NM_4T(device, slot)
                    elif value == 'Leopard-2FE':
                        device.slot[slot] = Leopard_2FE(device,slot)
                    elif value == 'NM-16ESW':
                        device.slot[slot] = NM_16ESW(device, slot)
                    else:
                        return False
                    return True
        elif type(device) == C2691:
            if option in ('slot0', 'slot1'):
                slot = int(option[4])
                if value == 'NM-1FE-TX':
                    device.slot[slot] = NM_1FE_TX(device, slot)
                elif value == 'NM-4T':
                    device.slot[slot] = NM_4T(device, slot)
                elif value == 'NM-16ESW':
                    device.slot[slot] = NM_16ESW(device, slot)
                else:
                    return False
                return True
        elif type(device) == C3725:
            if option in ('slot0', 'slot1', 'slot2'):
                slot = int(option[4])
                if value == 'NM-1FE-TX':
                    device.slot[slot] = NM_1FE_TX(device, slot)
                elif value == 'NM-4T':
                    device.slot[slot] = NM_4T(device, slot)
                elif value == 'NM-16ESW':
                    device.slot[slot] = NM_16ESW(device, slot)
                else:
                    return False
                return True
        elif type(device) == C3745:
            if option in ('slot0', 'slot1', 'slot2', 'slot3', 'slot4'):
                slot = int(option[4])
                if value == 'NM-1FE-TX':
                    device.slot[slot] = NM_1FE_TX(device, slot)
                elif value == 'NM-4T':
                    device.slot[slot] = NM_4T(device, slot)
                elif value == 'NM-16ESW':
                    device.slot[slot] = NM_16ESW(device, slot)
                else:
                    return False
                return True

    return False


def connect(router, source, dest):
    """ Connect a router to something
        router: a router object
        source: a string specifying the local interface
        dest: a string specifying a device and a remote interface, LAN, a raw NIO
    """

    match_obj = interface_re.search(source)
    if not match_obj:
        return False
    (pa1, slot1, port1) = match_obj.group(1,2,3)
    slot1 = int(slot1)
    port1 = int(port1)
    try:
        (devname, interface) = dest.split(' ')
    except ValueError:
        # Must be either a NIO or malformed
        if not dest[:4].lower() == 'nio_':
            debug('Malformed destination:' + str(dest))
            return False
        try:
            debug('A NETIO: ' + str(dest))
            (niotype, niostring) = dest.split(':',1)
        except ValueError:
            debug('Malformed NETIO:' + str(dest))
            return False
        # Process the netio
        if niotype.lower() == 'nio_linux_eth':
            debug('NIO_linux_eth ' + str(dest))
            smartslot(router, pa1, slot1, port1)
            router.slot[slot1].nio(port1, nio=NIO_linux_eth(router.dynamips, interface=niostring))

        elif niotype.lower() == 'nio_gen_eth':
            debug('gen_eth ' + str(dest))
            smartslot(router, pa1, slot1, port1)
            router.slot[slot1].nio(port1, nio=NIO_gen_eth(router.dynamips, interface=niostring))

        elif niotype.lower() == 'nio_udp':
            debug('udp ' + str(dest))
            (udplocal, remotehost, udpremote) = niostring.split(':',2)
            smartslot(router, pa1, slot1, port1)
            router.slot[slot1].nio(port1, nio=NIO_udp(router.dynamips, int(udplocal), str(remotehost), int(udpremote)))

        elif niotype.lower() == 'nio_null':
            debug('nio null')
            smartslot(router, pa1, slot1, port1)
            router.slot[slot1].nio(port1, nio=NIO_null(router.dynamips))

        elif niotype.lower() == 'nio_tap':
            debug('nio tap ' + str(dest))
            smartslot(router, pa1, slot1, port1)
            router.slot[slot1].nio(port1, nio=NIO_tap(router.dynamips, niostring))

        elif niotype.lower() == 'nio_unix':
            debug('unix ' + str(dest))
            (unixlocal, unixremote) = niostring.split(':',1)
            smartslot(router, pa1, slot1, port1)
            router.slot[slot1].nio(port1, nio=NIO_unix(router.dynamips, unixlocal, unixremote))

        elif niotype.lower() == 'nio_vde':
            debug('vde ' + str(dest))
            (controlsock, localsock) = niostring.split(':',1)
            smartslot(router, pa1, slot1, port1)
            router.slot[slot1].nio(port1, nio=NIO_vde(router.dynamips, controlsock, localsock))

        else:
            # Bad NIO
            return False
        return True

    match_obj = interface_re.search(interface)
    if match_obj:
        # Connecting to another interface
        (pa2, slot2, port2) = match_obj.group(1,2,3)
        slot2 = int(slot2)
        port2 = int(port2)

        # Does the device we are trying to connect to actually exist?
        if not devices.has_key(devname):
            line = router.name + ' ' + source + ' = ' + dest
            doerror('Nonexistant device "' + devname + '" in line: \n ' + line)

        # If interfaces don't exist, create them
        smartslot(router, pa1, slot1, port1)
        smartslot(devices[devname], pa2, slot2, port2)

        router.slot[slot1].connect(port1, devices[devname].dynamips, devices[devname].slot[slot2], port2)
        return True

    if devname.lower() == 'lan':
        debug('a LAN interface ' + str(dest))
        # If interface doesn't exist, create it
        smartslot(router, pa1, slot1, port1)
        if not bridges.has_key(interface):
            # If this LAN doesn't already exist, create it
            bridges[interface] = Bridge(router.dynamips, name=interface)
        router.slot[slot1].connect(port1, bridges[interface].dynamips, bridges[interface])
        return True

    match_obj = number_re.search(interface)
    if match_obj:
        port2 = int(interface)
        # Should be a swtich port
        if devname not in devices:
            debug('Unknown device ' + str(devname))
            return False

        debug('a switch port: ' + str(dest))
        # If interface doesn't exist, create it
        smartslot(router, pa1, slot1, port1)
        router.slot[slot1].connect(port1, devices[devname].dynamips, devices[devname], port2)
        return True

    else:
        # Malformed
        debug('Malformed destination interface: ' + str(dest))
        return False


def smartslot(router, pa, slot, port):
    """ Pick the right adapter for the desired interface type, and insert it
        router: a router object
        pa: a one or two character string 'fa', 'et', 'se', 'at', or 'po'
        slot: slot number
        port: port number
    """
    try:
        if router.slot[slot] != None:
            # Already a PA in this slot. No need to pick one.
            return True
    except:
        doerror("Invalid slot %i specified for device %s" % (slot, router.name))
    if pa[0].lower() == 'f':
        if router.model == 'c3600':
            if router.chassis == '3660' and slot == 0:
                router.slot[slot] = Leopard_2FE(router,slot)
            else:
                router.slot[slot] = NM_1FE_TX(router, slot)
        elif router.model in ['c2691', 'c3725', 'c3745']:
            if slot == 0:
                router.slot[slot] = GT96100_FE(router,slot)
            else:
                router.slot[slot] = NM_1FE_TX(router, slot)
        else:
            if slot == 0:
                router.slot[slot] = PA_C7200_IO_FE(router, slot)
            else:
                router.slot[slot] = PA_FE_TX(router, slot)
        return True
    if pa[0].lower() == 'e':
        if router.model == 'c3600':
            router.slot[slot] = NM_4E(router, slot)
        elif router.model in ['c2691', 'c3725', 'c3745']:
            doerror("Unsuppported interface %s%i/%i specified for device: %s" % (pa, slot, port, router.name))
        else:
            router.slot[slot] = PA_8E(router, slot)
        return True
    if pa[0].lower() == 's':
        if router.model in ['c2691', 'c3725', 'c3745', 'c3600']:
            router.slot[slot] = NM_4T(router, slot)
        else:
            router.slot[slot] = PA_8T(router, slot)
        return True
    if pa[0].lower() == 'a':
        if router.model in ['c2691', 'c3725', 'c3745', 'c3600']:
            doerror("Unsuppported interface %s%i/%i specified for device: %s" % (pa, slot, port, router.name))
        router.slot[slot] = PA_A1(router, slot)
        return True
    if pa[0].lower() == 'p':
        if router.model in ['c2691', 'c3725', 'c3745', 'c3600']:
            doerror("Unsuppported interface %s%i/%i specified for device: %s" % (pa, slot, port, router.name))
        router.slot[slot] = PA_POS_OC3(router, slot)
        return True
    # Bad pa passed
    return False


def switch_map(switch, source, dest):
    """ Apply a Frame Relay or ATM switch mapping
        switch: a FRSW or ATMSW instance
        source: a string specifying the source mapping
        dest: a string sepcifying the dest mapping
    """
    # Is this a FR / ATM vpi mapping?
    matchobj = mapint_re.search(source)
    if matchobj:
        (port1, map1) = map(int, matchobj.group(1,2))
        matchobj = mapint_re.search(dest)
        if not matchobj:
            print('*** Warning: ignoring invalid switch mapping entry %s = %s' % (source, dest))
            return False
        (port2, map2) = map(int, matchobj.group(1,2))
        if type(switch) == FRSW:
            # Forward
            switch.map(port1, map1, port2, map2)
            # And map the reverse
            switch.map(port2, map2, port1, map1)
            return True
        elif type(switch) == ATMSW:
            switch.mapvp(port1, map1, port2, map2)
            switch.mapvp(port2, map2, port1, map1)
            return True
        else:
            print('*** Warning: ignoring attempt to apply switch mapping to invalid device type: %s = %s' % (source, dest))
            return False
    # Is this an ATM VCI mapping?
    matchobj = mapvci_re.search(source)
    if matchobj:
        if type(switch) != ATMSW:
            print('*** Warning: ignoring invalid switch mapping entry %s = %s' % (source, dest))
            return False
        (port1, vp1, vc1) = map(int, matchobj.group(1,2,3))
        matchobj = mapvci_re.search(dest)
        if not matchobj:
            print('*** Warning: ignoring invalid switch mapping entry %s = %s' % (source, dest))
            return False
        (port2, vp2, vc2) = map(int, matchobj.group(1,2,3))
        if not matchobj:
            print('*** Warning: ignoring invalid switch mapping entry %s = %s' % (source, dest))
            return False
        switch.mapvc(port1, vp1, vc1, port2, vp2, vc2)
        switch.mapvc(port2, vp2, vc2, port1, vp1, vc1)
        return True

    print('*** Warning: ignoring invalid switch mapping entry %s = %s' % (source, dest))
    return False


def import_config(FILENAME):
    """ Read in the config file and set up the network
    """
    global globalconfig, globaludp, handled, debuglevel
    connectionlist = []     # A list of router connections
    maplist = []            # A list of Frame Relay and ATM switch mappings
    ethswintlist = []           # A list of Ethernet Switch vlan mappings

    # look for configspec in CONFIGSPECPATH and the same directory as dynagen
    realpath = os.path.realpath(sys.argv[0])
    debug('realpath ' + realpath)
    pathname = os.path.dirname(realpath)
    debug('pathname -> ' + pathname)
    CONFIGSPECPATH.append(pathname)
    for dir in CONFIGSPECPATH:
        configspec = dir +'/' + CONFIGSPEC
        debug('configspec -> ' + configspec)

        # Check to see if configuration file exists
        try:
            h=open(FILENAME)
            h.close()
            try:
                config = ConfigObj(FILENAME, configspec=configspec, raise_errors=True)
            except SyntaxError, e:
                print "\nError:"
                print e
                print e.line, '\n'
                raw_input("Press ENTER to continue")
                handled = True
                sys.exit(1)

        except IOError:
           #doerror("Can't open configuration file")
           continue

    vtor = Validator()
    res = config.validate(vtor, preserve_errors=True)
    if res == True:
        debug('Passed validation')
    else:
        for entry in flatten_errors(config, res):
            # each entry is a tuple
            section_list, key, error = entry
            if key is not None:
               section_list.append(key)
            else:
                section_list.append('[missing section]')
            section_string = ', '.join(section_list)
            if error == False:
                error = 'Missing value or section.'
            print section_string, ' = ', error
        raw_input("Press ENTER to continue")
        handled = True
        sys.exit(1)

    debuglevel = config['debug']
    if debuglevel > 0: setdebug(True)

    globalconfig = config           # Store the config in a global for access by console.py

    if debuglevel >= 3:
        debug("Top-level items:")
        for item in config.scalars:
            debug(item + ' = ' + str(config[item]))

    debug("Dynamips Servers:")
    for section in config.sections:
        server = config[section]
        server.host = server.name
        controlPort = None
        if ':' in server.host:
            # unpack the server and port
            (server.host, controlPort) = server.host.split(':')
        if debuglevel >= 3:
            debug("Server = " + server.name)
            for item in server.scalars:
                debug('  ' + str(item) + ' = ' + str(server[item]))
        try:
            if server['port'] != None:
                controlPort = server['port']
            if controlPort == None:
                controlPort = 7200
            dynamips[server.name] = Dynamips(server.host, int(controlPort))
            # Reset each server
            dynamips[server.name].reset()
        except DynamipsError:
            doerror('Could not connect to server: %s' % server.name)

        if server['udp'] != None:
            udp = server['udp']
        else:
            udp = globaludp
        # Modify the default base UDP NIO port for this server
        try:
            dynamips[server.name].udp = udp
        except DynamipsError:
            doerror('Could not set base UDP NIO port to: "%s" on server: %s' % (server['udp'], server.name))


        if server['workingdir'] == None:
            # If workingdir is not specified, set it to the same directory
            # as the network file

            realpath = os.path.realpath(FILENAME)
            workingdir = os.path.dirname(realpath)
        else:
            workingdir = server['workingdir']

        try:
            # Encase workingdir in quotes to protect spaces
            workingdir = '"' + workingdir + '"'
            dynamips[server.name].workingdir = workingdir
        except DynamipsError:
            doerror('Could not set working directory to: "%s" on server: %s' % (server['workingdir'], server.name))

        # Has the base console port been overridden?
        if server['console'] != None:
            dynamips[server.name].baseconsole = server['console']

        # Devices on this Dynamips server
        devdefaults = {}
        devdefaults['7200'] = {}          # A dictionary of the default options and values for 7200 routers on this server
        devdefaults['3620'] = {}          # Defaults for 3620s
        devdefaults['3640'] = {}          # And guess what? Defaults for 3640s
        devdefaults['3660'] = {}          # Does it need to be said?
        devdefaults['2691'] = {}
        devdefaults['3725'] = {}
        devdefaults['3745'] = {}

        # Apply lab global defaults to device defaults
        for model in devdefaults:
            devdefaults[model]['ghostios'] = config['ghostios']
            devdefaults[model]['ghostsize'] = config['ghostsize']
            if config['idlemax'] != None:
                devdefaults[model]['idlemax'] = config['idlemax']
            if config['idlesleep'] != None:
                devdefaults[model]['idlesleep'] = config['idlesleep']

        for subsection in server.sections:
            device = server[subsection]
            # Create the device

            if device.name in DEVICETUPLE:
                debug('Router defaults:')
                # Populate the appropriate dictionary
                for scalar in device.scalars:
                    if device[scalar] != None:
                        devdefaults[device.name][scalar] = device[scalar]
                continue

            debug(device.name)
            # Create the device
            try:
                (devtype, name) = device.name.split(' ')
            except ValueError:
                doerror('Unable to interpret line: "[[' + device.name + ']]"')

            if devtype.lower() == 'router':
                # if model not specifically defined for this router, set it to the default defined in the top level config
                if device['model'] == None:
                    device['model'] = config['model']

                # Note to self: rewrite this blob to be a little smarter and use the Router superclass
                if device['model'] == '7200':
                    dev = C7200(dynamips[server.name], name=name)
                    # Apply the router defaults to this router
                    setdefaults(dev, devdefaults['7200'])
                elif device['model'] == '3620':
                    dev = C3600(dynamips[server.name], chassis = device['model'], name=name)
                    # Apply the router defaults to this router
                    setdefaults(dev, devdefaults['3620'])
                elif device['model'] == '3640':
                    dev = C3600(dynamips[server.name], chassis = device['model'], name=name)
                    # Apply the router defaults to this router
                    setdefaults(dev, devdefaults['3640'])
                elif device['model'] == '3660':
                    dev = C3600(dynamips[server.name], chassis = device['model'], name=name)
                    # Apply the router defaults to this router
                    setdefaults(dev, devdefaults['3660'])
                elif device['model'] == '2691':
                    dev = C2691(dynamips[server.name], name=name)
                    # Apply the router defaults to this router
                    setdefaults(dev, devdefaults['2691'])
                elif device['model'] == '3725':
                    dev = C3725(dynamips[server.name], name=name)
                    # Apply the router defaults to this router
                    setdefaults(dev, devdefaults['3725'])
                elif device['model'] == '3745':
                    dev = C3745(dynamips[server.name], name=name)
                    # Apply the router defaults to this router
                    setdefaults(dev, devdefaults['3745'])

                if device['autostart'] == None:
                    autostart[name] = config['autostart']
                else:
                    autostart[name] = device['autostart']
            elif devtype.lower() == 'frsw':
                dev = FRSW(dynamips[server.name], name=name)
            elif devtype.lower() == 'atmsw':
                dev = ATMSW(dynamips[server.name], name=name)
            elif devtype.lower() == 'ethsw':
                dev = ETHSW(dynamips[server.name], name=name)
            else:
                print '\n***Error: unknown device type:', devtype, '\n'
                raw_input("Press ENTER to continue")
                handled = True
                sys.exit(1)
            devices[name] = dev

            for subitem in device.scalars:
                if device[subitem] != None:
                    debug('  ' + subitem + ' = ' + str(device[subitem]))
                    if setproperty(dev, subitem, device[subitem]):
                        # This was a property that was set.
                        continue
                    else:
                        # Should be either an interface connection or a switch mapping
                        # is it an interface?
                        if interface_re.search(subitem):
                            # Add the tuple to the list of connections to deal with later
                            connectionlist.append((dev, subitem, device[subitem]))
                        # is it a frame relay or ATM vpi mapping?
                        elif mapint_re.search(subitem) or mapvci_re.search(subitem):
                            # Add the tupple to the list of mappings to deal with later
                            maplist.append((dev, subitem, device[subitem]))
                        # is it an Ethernet switch port configuration?
                        elif ethswint_re.search(subitem):
                            ethswintlist.append((dev, subitem, device[subitem]))

                        else:
                            debug('***Warning: ignoring unknown config item: %s %s' % (str(subitem), str(device[subitem])))


    # Establish the connections we collected earlier
    for connection in connectionlist:
        debug('connection: ' + str(connection))
        (router, source, dest) = connection
        try:
            result = connect(router, source, dest)
        except DynamipsError, e:
            err = e[0]
            doerror('Connecting %s %s to %s resulted in \n    %s' % (router.name, source, dest, err))
        if result == False:
            doerror('Attempt to connect %s %s to unknown device: "%s"' % (router.name, source, dest))

    # Apply the switch configuration we collected earlier
    for mapping in maplist:
        debug('mapping: ' + str(mapping))
        (switch, source, dest) = mapping
        switch_map(switch, source, dest)

    for ethswint in ethswintlist:
        debug('ethernet switchport configing: ' + str(ethswint))
        (switch, source, dest) = ethswint

        parameters = len(dest.split(' '))
        if parameters == 2:
            # should be a porttype and a vlan
            (porttype, vlan) = dest.split(' ')
            try:
                switch.set_port(int(source), porttype, int(vlan))
            except DynamipsError, e:
                doerror(e)
            except DynamipsWarning, e:
                dowarning(e)

        elif parameters == 3:
            # Should be a porttype, vlan, and an nio
            (porttype, vlan, nio) = dest.split(' ')
            try:
                (niotype, niostring) = nio.split(':',1)
            except ValueError:
                doerror('Malformed NETIO in line: ' + str(source) + ' = ' + str(dest))
                return False
            debug('A NETIO: ' + str(nio))
            try:
                #Process the netio
                if niotype.lower() == 'nio_linux_eth':
                    debug('NIO_linux_eth ' + str(dest))
                    switch.nio(int(source), nio=NIO_linux_eth(switch.dynamips, interface=niostring), porttype=porttype, vlan=vlan)

                elif niotype.lower() == 'nio_gen_eth':
                    debug('gen_eth ' + str(dest))
                    switch.nio(int(source), nio=NIO_gen_eth(switch.dynamips, interface=niostring), porttype=porttype, vlan=vlan)

                elif niotype.lower() == 'nio_udp':
                    debug('udp ' + str(dest))
                    (udplocal, remotehost, udpremote) = niostring.split(':',2)
                    switch.nio(int(source), nio=NIO_udp(switch.dynamips, int(udplocal), str(remotehost), int(udpremote)), porttype=porttype, vlan=vlan)

                elif niotype.lower() == 'nio_null':
                    debug('nio null')
                    switch.nio(int(source), nio=NIO_null(switch.dynamips), porttype=porttype, vlan=vlan)

                elif niotype.lower() == 'nio_tap':
                    debug('nio tap ' + str(dest))
                    switch.nio(int(source), nio=NIO_tap(switch.dynamips, niostring), porttype=porttype, vlan=vlan)

                elif niotype.lower() == 'nio_unix':
                    debug('unix ' + str(dest))
                    (unixlocal, unixremote) = niostring.split(':',1)
                    switch.nio(int(source), nio=NIO_unix(switch.dynamips, unixlocal, unixremote), porttype=porttype, vlan=vlan)

                elif niotype.lower() == 'nio_vde':
                    debug('vde ' + str(dest))
                    (controlsock, localsock) = niostring.split(':',1)
                    switch.nio(int(source), nio=NIO_vde(switch.dynamips, controlsock, localsock), porttype=porttype, vlan=vlan)

                else:
                    # Bad NIO
                    doerror('Invalid NIO in Ethernet switchport config: %s = %s' % (source, dest))

            except DynamipsError, e:
                doerror(e)

        else:
            doerror('Invalid Ethernet switchport config: %s = %s' % (source, dest))


def import_ini(FILENAME):
    """ Read in the INI file
    """
    global telnetstring, globaludp, useridledbfile, handled

    # look for the INI file in the same directory as dynagen
    realpath = os.path.realpath(sys.argv[0])
    pathname = os.path.dirname(realpath)
    debug('pathname -> ' + realpath)
    INIPATH.append(pathname)
    for dir in INIPATH:
        inifile = dir +'/' + FILENAME

        # Check to see if configuration file exists
        try:
            debug('INI -> ' + inifile)
            h=open(inifile)
            h.close()
            break
        except IOError:
            continue
    else:
       doerror("Can't open INI file")

    try:
        config = ConfigObj(inifile, raise_errors=True)
    except SyntaxError, e:
        print "\nError:"
        print e
        print e.line, '\n'
        raw_input("Press ENTER to continue")
        handled = True
        sys.exit(1)

    try:
        telnetstring = config['telnet']
    except KeyError:
        raise DynamipsError, "No telnet option found in INI file.\n"

    try:
        globaludp = int(config['udp'])
    except KeyError:
        pass
    except ValueError:
        dowarning("Ignoring invalid udp value in dynagen.ini")

    try:
        useridledbfile = config['idledb']
    except KeyError:
        # Set default to the home directory
        useridledbfile = os.path.expanduser('~' + os.path.sep + 'dynagenidledb.ini')


def import_generic_ini(inifile):
    """ Import a generic ini file and return it as a dictionary, if it exists
        Returns None if the file doesn't exit, or raises an error that can be handled
    """
    try:
        h=open(inifile, 'r')
        h.close()
    except IOError:
        # File does not exist, or is not readable
        return None

    try:
        config = ConfigObj(inifile, raise_errors=True)
    except SyntaxError, e:
        print "\nError in user idlepc database:"
        print e
        print e.line, '\n'
        raw_input("Press ENTER to continue")
        handled = True
        sys.exit(1)

    return config


def debug(string):
    """ Print string if debugging is true
    """
    global debuglevel
    # Level 3, dynagen debugs.
    if debuglevel >= 3: print '  DEBUG: ' + str(string)

def doerror(msg):
    global handled

    """Print out an error message"""
    print '\n*** Error:', str(msg)
    handled = True
    doreset()
    raw_input("Press ENTER to continue")
    sys.exit(1)

def dowarning(msg):
    """Print out minor warning messages"""
    print 'Warning:', str(msg)

def doreset():
    """reset all hypervisors"""
    for d in dynamips.values():
        d.reset()

if __name__ == "__main__":
    # Catch and display any unhandled tracebacks for bug reporting.
    try:
        # Get command line options
        usage = "usage: %prog [options] <config file>"
        parser = OptionParser(usage=usage, version="%prog " + VERSION)
        parser.add_option("-d", "--debug", action="store_true", dest="debug",
                      help="output debug info")
        parser.add_option("-n", "--nosend", action="store_true", dest="nosend",
                      help="do not send any command to dynamips")
        try:
            (options, args) = parser.parse_args()
        except SystemExit:
            handled = True
            sys.exit(0)

        if len(args) != 1:
            parser.print_help()
            handled = True
            sys.exit(1)

        FILENAME = args[0]
        if options.debug:
            setdebug(True)
            print "\nPython version: %s" % sys.version
        if options.nosend: nosend(True)

        # Check to see if the network file exists and is readable
        try:
            h = open(FILENAME, 'r')
            h.close()
        except IOError:
            doerror('Could not open file: ' + FILENAME)

        # Import INI file
        try:
            import_ini(INIFILE)
        except DynamipsError, e:
            doerror(e)

        print "\nReading configuration file...\n"
        try:
            import_config(FILENAME)
        except DynamipsError, e:
            # Strip leading error code if present
            e = str(e)
            if e[3] == '-':
                e = e[4:]
            doerror(e)

        # Read in the user idlepc database, if it exists
        useridledb = import_generic_ini(useridledbfile)

        # Push configurations stored in the network file
        if configurations != {}:
            result = raw_input("There are saved configurations in your network file. \nDo you wish to import them (Y/N)? ")
            if result.lower() == 'y':
                for routerName in configurations:
                    device = devices[routerName]
                    device.config_b64 = configurations[routerName]

        # Implement IOS Ghosting
        ghosts = {}         # a dictionary of ghost instances which will match the image name+hostname+port
        try:
            # If using mmap, create ghost IOS instances and apply it to instances that use them
            for device in devices.values():
                try:
                    if device.mmap == False:
                        continue
                except AttributeError:
                    # This device doesn't have an mmap property
                    continue

                if not ghosteddevices[device.name]:
                    continue

                if device.imagename == None:
                    doerror("No IOS image specified for device: " + device.name)

                ghostinstance = device.imagename + '-' + device.dynamips.host
                ghost_file = device.imagename + '.ghost'
                if ghostinstance not in ghosts:
                    # Only create a ghost if at least two instances on this server use this image
                    ioscount = 0
                    maxram = 0
                    for router in devices.values():
                        try:
                            if (router.dynamips.host == device.dynamips.host) and (router.imagename == device.imagename):
                                if ghosteddevices[router.name]:
                                    ioscount += 1
                                    if router.ram > maxram: maxram = router.ram
                        except AttributeError:
                            continue
                    if ioscount < 2:
                        ghosts[ghostinstance] = False
                    else:
                        # Create a new ghost
                        ghosts[ghostinstance] = True
                        ghost = Router(device.dynamips, device.model, 'ghost-'+ ghostinstance, consoleFlag = False)
                        ghost.image = device.image
                        ghost.ghost_status = 1
                        ghost.ghost_file = ghost_file
                        if ghostsizes[device.name] == None:
                            ghost.ram = maxram
                        else:
                            ghost.ram = ghostsizes[device.name]
                        ghost.start()
                        ghost.stop()
                        ghost.delete()
                # Reference the appropriate ghost for the image and dynamips server, if the multiple IOSs flag is true
                if ghosts[ghostinstance]:
                    device.ghost_status = 2
                    device.ghost_file = ghost_file
        except DynamipsError, e:
            doerror(e)

        # Apply idlepc values, and if necessary start the instances
        for device in devices.values():
            try:
                if device.idlepc == None:
                    if useridledb and device.imagename in useridledb:
                        device.idlepc = useridledb[device.imagename]
            except AttributeError:
                pass

            if autostart.has_key(device.name):
                if autostart[device.name]:
                    try:
                        if device.idlepc == None:
                            dowarning("Starting %s with no idle-pc value" % device.name)
                        device.start()
                    except DynamipsError, e:
                        doerror(e)

        print "\nNetwork successfully started\n"

        console = Console()
        try:
            console.cmdloop()
        except KeyboardInterrupt:
            print "Exiting..."

        doreset()
    except:
        # Display the unhandled exception, and pause so it can be observed
        if not handled:
            print """*** Dynagen has crashed ****
Please open a bug report against Dynagen at http://www.ipflow.utc.fr/bts/
Include a description of what you were doing when the error occured, your
network file, any errors output by dynamips, and the following traceback data:
            """

            exctype, value, trace = sys.exc_info()
            #print trace
            #tracestring = traceback.format_exc() #This only works in 2.4
            traceback.print_exc()
            raw_input("Press ENTER to exit")

            if debuglevel >=2:
                print "\nDumping namespace..."
                print 'Globals:'
                print trace.tb_frame.f_globals
                print 'Locals:'
                print trace.tb_frame.f_locals

            sys.exit(1)

