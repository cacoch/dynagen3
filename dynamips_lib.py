#!/usr/bin/env python

"""
dynamips_lib.py
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

import sys, os, re, base64
from socket import socket, timeout, AF_INET, SOCK_STREAM

version = "0.8.2.112806"
NOSEND = False       # Disable sending any commands to the back end for debugging
DEBUG = False

# Constants for use with router.idleprop
IDLEPROPGET = 0
IDLEPROPSHOW = 1
IDLEPROPSET = 3

error_re = re.compile(r"""^2[0-9][0-9]-""")
last_re = re.compile(r"""^[1-2][0-9][0-9]-""")

# determine if we are in the debugger
try:
    DBGPHideChildren
except NameError:
    DEBUGGER = False
else:
    DEBUGGER = True

class Dynamips(object):
    """ Creates a new connection to a Dynamips server
        host: the hostname or ip address of the Dynamips server
        port: the tcp port (defaults to 7200)
        timeout: how log to wait for a response to commands sent to the server
                 default is 3 seconds
    """
    def __init__(self, host, port=7200, timeout=300):
        self.s = socket(AF_INET, SOCK_STREAM)
        self.s.setblocking(0)
        self.s.settimeout(timeout)
        if not NOSEND:
            try:
                self.s.connect((host,port))
            except:
                raise DynamipsError("Could not connect to server")
        self.__devices = []
        self.__workingdir = ''
        self.__host = host
        self.__port = port
        self.__baseconsole = 2000
        self.__udp = 10000
        try:
            self.__version = send(self, 'hypervisor version')[0][4:]
        except IndexError:
            # Probably because NOSEND is set
            self.__version = 'N/A'

    def close(self):
        """ Close the connection to the Hypervisor (but leave it running)
        """
        result = send(self, 'hypervisor close')
        self.s.close()


    def reset(self):
        """ reset the hypervisor
        """
        result = send(self, 'hypervisor reset')

    def stop(self):
        """ Shut down the hypervisor
        """
        result = send(self, 'hypervisor stop')
        self.s.close()

    def __setdevices(self, devices):
        """ Set the list of devices managed by this dynamips instance
            This method is for internal use by Router.__init__
            devices: (list) a list of device objects
        """
        self.__devices = devices

    def __getdevices(self):
        """ Returns the list of devices managed by this dynamips instance
        """
        return self.__devices

    devices = property(__getdevices, __setdevices, doc = 'The list of devices managed by this dynamips instance')


    def __setworkingdir(self, directory):
        """ Set the working directory for this network
            directory: (string) the directory
        """
        if type(directory) != str:
            raise DynamipsError('invalid directory')
        self.__workingdir = directory
        send(self, 'hypervisor working_dir %s' % self.__workingdir)

    def __getworkingdir(self):
        """ Returns working directory
        """
        return self.__workingdir

    workingdir = property(__getworkingdir, __setworkingdir, doc = 'The working directory')


    def __setbaseconsole(self, baseconsole):
        """ Set the base console TCP port for this server
            directory: (int) the starting console port number
        """
        if type(baseconsole) != int:
            raise DynamipsError('invalid console port')
        self.__baseconsole = baseconsole

    def __getbaseconsole(self):
        """ Returns working directory
        """
        return self.__baseconsole

    baseconsole = property(__getbaseconsole, __setbaseconsole, doc = 'The starting console port')


    def __setudp(self, udp):
        """ Set the next open UDP port for NIOs for this server
            udp: (int) the next NIO udp port
        """
        if type(udp) != int:
            raise DynamipsError('invalid UDP port')
        self.__udp = udp

    def __getudp(self):
        """ Returns the next available UDP port for NIOs
        """
        return self.__udp

    udp = property(__getudp, __setudp, doc = 'The next available UDP port for NIOs')


    def list(self, subsystem):
        """ Send a generic list command to Dynamips
            subsystem is one of nio, frsw, atmsw
        """
        result = send(self, subsystem + " list")
        return result


    def send_raw(self, string):
        """ Send a raw command to Dynamips. Use sparingly.
        """
        result = send(self, string)
        return result


    def __gethost(self):
        """ Returns the host property
        """
        return self.__host

    host = property(__gethost, doc = 'The dynamips host IP or name')

    def __getport(self):
        """ Returns the port property
        """
        return self.__port

    port = property(__getport, doc = 'The dynamips port')


    def __getversion(self):
        """ Returns dynamips version
        """
        return self.__version

    version = property(__getversion, doc = 'The dynamips version')


class NIO_udp(object):
    """ Create a nio_udp object
        dynamips: the dynamips server object
        udplocal: (int) local udp port
        remotehost: (string) host or ip address of remote
        udpremote: (int) remote udp port
        name: (string) optional name for this object
    """
    __instance = 0

    def __init__(self, dynamips, udplocal, remotehost, udpremote, name = None):
        self.__d = dynamips
        self.__udplocal = udplocal
        self.__remotehost = remotehost
        self.__udpremote = udpremote
        self.__instance = NIO_udp.__instance
        NIO_udp.__instance += 1
        if name == None:
            self.__name = 'nio_udp' + str(self.__instance)
        else:
            self.__name = name

        send(self.__d, 'nio create_udp %s %i %s %i' % (self.__name, self.__udplocal, self.__remotehost, self.__udpremote))


    def __getudplocal(self):
        return self.__udplocal
    udplocal = property(__getudplocal)

    def __getremotehost(self):
        return self.__remotehost
    remotehost = property(__getremotehost)

    def __getudpremote(self):
        return self.__udpremote
    udpremote = property(__getudpremote)

    def __getname(self):
        return self.__name
    name = property(__getname)


class NIO_linux_eth(object):
    """ Create a nio_linux_eth object
        dynamips: the dynamips server object
        interface: (string) the interface on this linux host
        name: (string) optional name for this object
    """
    __instance = 0

    def __init__(self, dynamips, interface, name = None):
        self.__d = dynamips
        self.__interface = interface
        self.__instance = NIO_linux_eth.__instance
        NIO_linux_eth.__instance += 1
        if name == None:
            self.__name = 'nio_linux_eth' + str(self.__instance)
        else:
            self.__name = name

        send(self.__d, 'nio create_linux_eth %s %s' % (self.__name, self.__interface))


    def __getinterface(self):
        return self.__interface
    interface = property(__getinterface)

    def __getname(self):
        return self.__name
    name = property(__getname)


class NIO_gen_eth(object):
    """ Create a nio_gen_eth object
        dynamips: the dynamips server object
        interface: (string) the interface on this host
        name: (string) optional name for this object
    """
    __instance = 0

    def __init__(self, dynamips, interface, name = None):
        self.__d = dynamips
        self.__interface = interface
        self.__instance = NIO_gen_eth.__instance
        NIO_gen_eth.__instance += 1
        if name == None:
            self.__name = 'nio_gen_eth' + str(self.__instance)
        else:
            self.__name = name
        send(self.__d, 'nio create_gen_eth %s %s' % (self.__name, self.__interface))


    def __getinterface(self):
        return self.__interface
    interface = property(__getinterface)

    def __getname(self):
        return self.__name
    name = property(__getname)

class NIO_tap(object):
    """ Create a nio_tap object
        dynamips: the dynamips server object
        tap: (string) the tap device
        name: (string) optional name for this object
    """
    __instance = 0

    def __init__(self, dynamips, tap, name = None):
        self.__d = dynamips
        self.__interface = tap
        self.__instance = NIO_tap.__instance
        NIO_tap.__instance += 1
        if name == None:
            self.__name = 'nio_tap' + str(self.__instance)
        else:
            self.__name = name

        send(self.__d, 'nio create_tap %s %s' % (self.__name, self.__interface))


    def __getinterface(self):
        return self.__interface
    interface = property(__getinterface)

    def __getname(self):
        return self.__name
    name = property(__getname)

class NIO_unix(object):
    """ Create a nio_unix object
        dynamips: the dynamips server object
        unixlocal: local unix socket
        unixremote: remote unix socket
        name: (string) optional name for this object
    """
    __instance = 0

    def __init__(self, dynamips, unixlocal, unixremote, name = None):
        self.__d = dynamips
        self.__unixlocal = unixlocal
        self.__unixremote = unixremote
        self.__instance = NIO_unix.__instance
        NIO_unix.__instance += 1
        if name == None:
            self.__name = 'nio_unix' + str(self.__instance)
        else:
            self.__name = name

        send(self.__d, 'nio create_unix %s %s %s' % (self.__name, self.__unixlocal, self.__unixremote))


    def __getunixlocal(self):
        return self.__unixlocal
    unixlocal = property(__getunixlocal)

    def __getunixremote(self):
        return self.__unixremote
    unixremote = property(__getunixremote)

    def __getname(self):
        return self.__name
    name = property(__getname)

class NIO_vde(object):
    """ Create a nio_vde object
        dynamips: the dynamips server object
        controlsock: control socket
        localsock: local socket
        name: (string) optional name for this object
    """
    __instance = 0

    def __init__(self, dynamips, controlsock, localsock, name = None):
        self.__d = dynamips
        self.__controlsock = controlsock
        self.__localsock = localsock
        self.__instance = NIO_vde.__instance
        NIO_vde.__instance += 1
        if name == None:
            self.__name = 'NIO_vde' + str(self.__instance)
        else:
            self.__name = name

        send(self.__d, 'nio create_vde %s %s %s' % (self.__name, self.__controlsock, self.__localsock))


    def __getcontrolsock(self):
        return self.__controlsock
    controlsock = property(__getcontrolsock)

    def __getlocalsock(self):
        return self.__localsock
    localsock = property(__getlocalsock)

    def __getname(self):
        return self.__name
    name = property(__getname)


class NIO_null(object):
    """ Create a nio_nulll object
        dynamips: the dynamips server object
        name: (string) optional name for this object
    """
    __instance = 0

    def __init__(self, dynamips, name = None):
        self.__d = dynamips
        self.__instance = NIO_null.__instance
        NIO_null.__instance += 1
        if name == None:
            self.__name = 'nio_null' + str(self.__instance)
        else:
            self.__name = name

        send(self.__d, 'nio create_null %s' % self.__name)


    def __getname(self):
        return self.__name
    name = property(__getname)


class BaseAdapter(object):
    """ The base adapter object
        router: A Router object
        slot: An int specifying the slot
        adapter: the adapter or network module model
        ports: the number of ports
    """
    def __init__(self, router, slot, adapter, ports, bindingcommand):
        self.__adapter = adapter
        self.__router = router
        self.__slot = slot
        self.ports = [None] * ports
        self.__nios = [None] * ports

        if bindingcommand != None:
            send(router.dynamips, '%s %s %s %i %s' % (router.model, bindingcommand, router.name, slot, adapter))


    def __getrouter(self):
        """ Returns the router this adapter is part of
        """
        return self.__router

    router = property(__getrouter, doc = 'This adapters host router')

    def __getadapter(self):
        """ Returns the adapter property
        """
        return self.__adapter

    adapter = property(__getadapter, doc = 'The port adapter')


    def __getslot(self):
        """ Returns the slot property
        """
        return self.__slot

    slot = property(__getslot, doc = 'The slot in which this adapter is inserted')


    def connect(self, localport, remoteserver, remoteadapter, remoteport = None):
        """ Connect this port to a port on another device
            localport: A port on this adapter
            remoteserver: the dynamips object that hosts the remote adapter
            remoteadapter: An adapter or module object on another device (router, bridge, or switch)
            remoteport: A port on the remote adapter (only for routers or switches)
        """

        # Call the generalized connect function
        d = self.__router
        gen_connect(src_dynamips = self.__router.dynamips,
                    src_adapter = self,
                    src_port = localport,
                    dst_dynamips = remoteserver,
                    dst_adapter = remoteadapter,
                    dst_port = remoteport)

    def filter(self, port, filterName, direction, options = None):
        """ Apply a connection filter to this interface
            port: a port on this adapter or module
            filterName: The name of the filter
            direction: 'in' for rx, 'out' for tx
            options: a list of options to pass to this filter
        """

        filters = ['freq_drop', 'none']      # a list of the known filters
        filterName = filterName.lower()
        if filterName not in filters:
            raise DynamipsError('invalid filter')
        direction = direction.lower()
        if direction not in ['in', 'out']:
            raise DynamipsError('invalid filter direction')

        # Determine the nio
        try:
            nioName = self.nio(port).name
        except AttributeError:
            raise DynamipsError('Invalid interface')

        if direction == 'in':
            dirint = 0
        else:
            dirint = 1

        d = self.router.dynamips

        # First bind the filter
        # e.g. nio bind_filter nio_udp1 0 freq_drop
        if filterName == 'none':
            # unbind any filters
            send(d, 'nio unbind_filter %s %s' % (nioName, dirint))
            return
        else:
            send(d, 'nio bind_filter %s %s %s' % (nioName, dirint, filterName))

        # Next, setup the filter
        # e.g nio setup_filter nio_udp1 0 50
        if options == None:
            optstring == ''
        send(d, 'nio setup_filter %s %s %s' % (nioName, dirint, options))


    def nio(self, port, nio = None):
        """ Returns the NETIO object for this port
            or if nio is set, sets the NETIO for this port
            port: a port on this adapter or module
            nio: optional NETIO object to assign
        """
        if port < 0 or port > len(self.ports) - 1:
            raise DynamipsError('invalid port')

        if nio == None:
            # Return the NETIO string
            try:
                return self.__nios[port]
            except KeyError:
                raise DynamipsError('port does not exist on this PA or module')
        nio_t = type(nio)
        if nio_t == NIO_udp or nio_t == NIO_linux_eth or nio_t == NIO_gen_eth or nio_t == NIO_tap or nio_t == NIO_unix or nio_t == NIO_vde:
            send(self.__router.dynamips, '%s add_nio_binding %s %i %i %s' % (self.__router.model, self.__router.name, self.slot, port, nio.name))
        else:
            raise DynamipsError('invalid NETIO')

        # Set the NETIO for this port
        self.__nios[port] = nio


    def connected(self, port):
        """ Returns a boolean indicating a port on this adapter is connected or not
        """
        return connected_general(self, port)


class PA(BaseAdapter):
    """ Creates a Router Port Adapter
        router: A Router object
        slot: An int specifying the slot (0-6)
        adapter: the adapter model
        ports: the number of ports
    """
    def __init__(self, router, slot, adapter, ports):
        BaseAdapter.__init__(self, router, slot, adapter, ports, 'add_pa_binding')


class PA_C7200_IO_FE(PA):
    """ A C7200-IO-FE FastEthernet adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot != 0:
            raise DynamipsError('invalid slot. C7200-IO-FE only supported in slot 0')
        PA.__init__(self, router, slot, 'C7200-IO-FE', 1)


class PA_A1(PA):
    """ A PA-A1 FastEthernet adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot < 1 or slot >6:
            raise DynamipsError('invalid slot. PA-A1 only supported in slots 1-6')
        PA.__init__(self, router, slot, 'PA-A1', 1)


class PA_FE_TX(PA):
    """ A PA-FE-TX FastEthernet adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot < 1 or slot >6:
            raise DynamipsError('invalid slot. PA-FE-TX only supported in slots 1-6')
        PA.__init__(self, router, slot, 'PA-FE-TX', 1)


class PA_4T(PA):
    """ A PA_4T+ 4-port serial adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot < 1 or slot >6:
            raise DynamipsError('invalid slot. PA-4T+ only supported in slots 1-6')
        PA.__init__(self, router, slot, 'PA-4T+', 4)


class PA_8T(PA):
    """ A PA_8T 8-port serial adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot < 1 or slot >6:
            raise DynamipsError('invalid slot. PA-8T only supported in slots 1-6')
        PA.__init__(self, router, slot, 'PA-8T', 8)


class PA_4E(PA):
    """ A PA_4E 4-port ethernet adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot < 1 or slot >6:
            raise DynamipsError('invalid slot. PA-4E only supported in slots 1-6')
        PA.__init__(self, router, slot, 'PA-4E', 4)


class PA_8E(PA):
    """ A PA_8E 4-port ethernet adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot < 1 or slot >6:
            raise DynamipsError('invalid slot. PA-8E only supported in slots 1-6')
        PA.__init__(self, router, slot, 'PA-8E', 8)


class PA_POS_OC3(PA):
    """ A PA-POS-OC3 adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot < 1 or slot >6:
            raise DynamipsError('invalid slot. PA-POS-OC3 only supported in slots 1-6')
        PA.__init__(self, router, slot, 'PA-POS-OC3', 1)


#***********************************************************************************************
class NM(BaseAdapter):
    """ A C2691/C3725/C3745/C3600 Network Module base object.
        Derived from the C7200 port adapter, with methods overridden where necessary
        router: A Router object
        slot: An int specifying the slot
        module: the network module model
        ports: the number of ports
    """
    def __init__(self, router, slot, module, ports):
        if router.model == 'c3600':
            if router.chassis == '3660' and module != 'Leopard-2FE':
                if slot == 0:
                    raise DynamipsError('invalid slot. %s only supported in slots 1-6 on the 3660' % module)

        if module == 'GT96100-FE':
            bindingcommand = None       # the GT96100-FE is already integrated
        else:
            bindingcommand = 'add_nm_binding'
        BaseAdapter.__init__(self, router, slot, module, ports, bindingcommand)

class Leopard_2FE(NM):
    """ Integrated 3660 2 Port FastEthernet adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot != 0 or router.chassis != '3660':
            raise DynamipsError('invalid slot. Leopard-2FE only supported in slot 0 on a 3660')
        NM.__init__(self, router, slot, 'Leopard-2FE', 2)


class NM_1FE_TX(NM):
    """ A NM-1FE-TX FastEthernet adapter
    """
    def __init__(self, router, slot):
        NM.__init__(self, router, slot, 'NM-1FE-TX', 1)


class NM_1E(NM):
    """ A NM-1E Ethernet adapter
    """
    def __init__(self, router, slot):
        NM.__init__(self, router, slot, 'NM-1E', 1)


class NM_4E(NM):
    """ A NM-4E Ethernet adapter
    """
    def __init__(self, router, slot):
        NM.__init__(self, router, slot, 'NM-4E', 4)


class NM_4T(NM):
    """ A NM-4T Ethernet adapter
    """
    def __init__(self, router, slot):
        NM.__init__(self, router, slot, 'NM-4T', 4)


class NM_16ESW(NM):
    """ A NM-16ESW Ethernet adapter
    """
    def __init__(self, router, slot):
        NM.__init__(self, router, slot, 'NM-16ESW', 16)


class GT96100_FE(NM):
    """ Integrated GT96100-FE 2691/3725/3745 2 Port FastEthernet adapter
    """
    def __init__(self, router, slot):
        if type(slot) != int or slot != 0 or router.model not in ['c2691', 'c3725', 'c3745']:
            raise DynamipsError('invalid slot. GT96100-FE only supported in slot 0 on a 2691/3725/3745')
        NM.__init__(self, router, slot, 'GT96100-FE', 2)


class Router(object):
    """ Creates a new Router instance
        dynamips: a Dynamips object
        model: Router model number (currently only c7200 is supported)
        console (optional): TCP port that attaches to this router's console.
                            Defaults to TCP 2000 + the instance number
        name (optional): An optional name. Defaults to the instance number
    """
    __instance_count = 0


    def __init__(self, dynamips, model = 'c7200', name = None, consoleFlag = True):
        if not isinstance(dynamips, Dynamips):
            raise DynamipsError('not a Dynammips instance')
        self.__d = dynamips
        self.__instance = Router.__instance_count
        Router.__instance_count += 1

        if model in ('c2691', 'c3725', 'c3745', 'c3600', 'c7200'):
            self.__model = model
        else:
            raise DynamipsError('invalid router model')

        if name == None:
            self.__name = 'r' + str(self.__instance)
        else:
            self.__name = name

        self.__cnfg = None
        self.__conf = '0x2102'
        self.__mac = None
        self.__clock = None
        self.__aux = None
        self.__image = None
        self.__idlepc = None
        self.__exec_area = None         # Means it is set to the default for your platform
        self.__mmap = True
        self.__state = 'stopped'
        self.__ghost_status = 0
        self.__idlemax = 1500
        self.__idlesleep = 30

        send(self.__d, '%s create %s %i' % (model, name, self.__instance))
        # Ghosts don't get console ports
        if consoleFlag:
            # Set the default console port. We'll try to use the base console port
            # plus the instance id, unless that is already taken
            console = self.__d.baseconsole + self.__instance
            while(True):
                conflict = checkconsole(console, self.__d)
                if conflict == None:
                    self.__console = console
                    send(self.__d, 'vm set_con_tcp_port %s %i' % (self.__name, console))
                    break
                else:
                    console += 1

        # Append this router to the list of devices managed by this dynamips instance
        self.__d.devices.append(self)


    def setdefaults(self, ram, nvram, disk0, disk1, npe = None, midplane = None):
        """ Set the default values for this router
        """
        self.__ram = ram
        self.__nvram = nvram
        self.__disk0 = disk0
        self.__disk1 = disk1
        self.__npe = npe
        self.__midplane = midplane


    def createslots(self, numslots):
        """ Create the appropriate number of sots for this router
        """
        self.slot = [None] * numslots


    def delete(self):
        """ Delete this router instance from the back-end
        """
        send(self.__d, "%s delete %s" % (self.__model, self.__name))


    def start(self):
        """ Start this instance
        """
        if self.__state == 'running':
            raise DynamipsError('router "%s" is already running' % self.name)
        if self.__state == 'suspended':
            raise DynamipsError('router "%s" is suspended and cannot be started. Use Resume.' % self.name)

        r = send(self.__d, "%s start %s" % (self.__model, self.__name))
        self.__state = 'running'
        return r


    def stop(self):
        """ Stop this instance
        """
        if self.__state == 'stopped':
            raise DynamipsError('router "%s" is already stopped' % self.name)

        r = send(self.__d, "%s stop %s" % (self.__model, self.__name))
        self.__state = 'stopped'
        return r

    def suspend(self):
        """ Suspend this instance
        """
        if self.__state == 'suspended':
            raise DynamipsError('router "%s" is already suspended' % self.name)
        if self.__state == 'stopped':
            raise DynamipsError('router "%s" is stopped and cannot be suspended' % self.name)

        r = send(self.__d, "vm suspend %s" % self.__name)
        self.__state = 'suspended'
        return r


    def resume(self):
        """ Resume this instance
        """
        if self.__state == 'running':
            raise DynamipsError('router "%s" is already running' % self.name)
        if self.__state == 'stopped':
            raise DynamipsError('router "%s" is stopped and cannot be resumed' % self.name)

        r = send(self.__d, "vm resume %s" %self.__name)
        self.__state = 'running'
        return r

    def idleprop(self, function, value = None):
        """ get, show, or set the online idlepc value
        """
        if self.__state == 'stopped':
            raise DynamipsError('router "%s" is stopped. Idle-pc functions can only be used on running routers' % self.name)

        if function == IDLEPROPGET:
            r = send(self.__d, "vm get_idle_pc_prop %s 0" % self.__name)
            return r
        elif function == IDLEPROPSHOW:
            r = send(self.__d, "vm show_idle_pc_prop %s 0" % self.__name)
            return r
        elif function == IDLEPROPSET:
            r = send(self.__d, "vm set_idle_pc_online %s 0 %s" % (self.__name, value))
            self.__idlepc = value
            return r

    def __setconsole(self, console):
        """ Set console port
            console: (int) TCP port of console
        """
        if type(console) != int or console < 1 or console > 65535:
            raise DynamipsError('invalid console port')

        # Check to see if the console port is already in use first
        conflict = checkconsole(console, self.__d)
        if conflict != None:
            # Is it this device that is causing the conflict? If so ignore it
            if conflict != self:
                raise DynamipsError("console port %i is already in use by device: %s" % (console, conflict.name))

        self.__console = console
        send(self.__d, 'vm set_con_tcp_port %s %i' % (self.__name, self.__console))

    def __getconsole(self):
        """ Returns console port
        """
        return self.__console

    console = property(__getconsole, __setconsole, doc = 'The router console port')

    def __setaux(self, aux):
        """ Set aux port
            aux: (int) TCP port of the aux port
        """
        if type(aux) != int or aux < 1 or aux > 65535:
            raise DynamipsError('invalid aux port')
        self.__aux = aux
        send(self.__d, 'vm set_aux_tcp_port %s %i' % (self.__name, self.__aux))

    def __getaux(self):
        """ Returns aux port
        """
        return self.__aux

    aux = property(__getaux, __setaux, doc = 'The router aux port')


    def __setram(self, ram):
        """ Set amount of RAM allocated to this router
            ram: (int) amount of RAM in MB
        """
        if type(ram) != int or ram < 1:
            raise DynamipsError('invalid ram size')
        self.__ram = ram
        send(self.__d, 'vm set_ram %s %i' % (self.__name, self.__ram))

    def __getram(self):
        """ Returns the amount of RAM allocated to this router
        """
        return self.__ram

    ram = property(__getram, __setram, doc = 'The amount of RAM allocated to this router')


    def __setdisk0(self, disk0):
        """ Set size of PCMCIA ATA disk0
            disk0: (int) amount of disk0 in MB
        """
        if type(disk0) != int or disk0 < 0:
            raise DynamipsError('invalid disk0 size')
        self.__disk0 = disk0
        send(self.__d, 'vm set_disk0 %s %i' % (self.__name, self.__disk0))

    def __getdisk0(self):
        """ Returns the disk0 size on this router
        """
        return self.__disk0

    disk0 = property(__getdisk0, __setdisk0, doc = 'The disk0 size on this router')


    def __setdisk1(self, disk1):
        """ Set size of PCMCIA ATA disk1
            disk1: (int) amount of disk1 in MB
        """
        if type(disk1) != int or disk1 < 0:
            raise DynamipsError('invalid disk1 size')
        self.__disk1 = disk1
        send(self.__d, 'vm set_disk1 %s %i' % (self.__name, self.__disk1))

    def __getdisk1(self):
        """ Returns the disk1 size on this router
        """
        return self.__disk1

    disk1 = property(__getdisk1, __setdisk1, doc = 'The disk1 size on this router')

    def __setclock(self, clock):
        """ Set the clock property
            clock: (int) clock divisor
        """
        if type(clock) != int or clock < 1:
            raise DynamipsError('invalid clock')
        self.__clock = clock
        send(self.__d, 'vm set_clock_divisor %s %i' % (self.__name, self.__clock))

    def __getclock(self):
        """ Returns clock property
        """
        return self.__clock

    clock = property(__getclock, __setclock, doc = 'The clock property of this router')


    def __setmmap(self, mmap):
        """ Set the mmap property
            mmap: (boolean) Map dynamic memory to a file or not
        """
        if type(mmap) != bool:
            raise DynamipsError('invalid mmap')
        self.__mmap = mmap
        if mmap == True:
            flag = 1
        else:
            flag = 0
        send(self.__d, 'vm set_ram_mmap %s %i' % (self.__name, flag))

    def __getmmap(self):
        """ Returns mmap property
        """
        return self.__mmap

    mmap = property(__getmmap, __setmmap, doc = 'The mmap property of this router')


    def __setnpe(self, npe):
        """ Set the npe property
            npe: (string) Set the NPE type
        """
        if type(npe) != str or npe not in ['npe-100', 'npe-150', 'npe-175', 'npe-200', 'npe-225', 'npe-300', 'npe-400']:
            raise DynamipsError('invalid NPE type')
        self.__npe = npe
        send(self.__d, '%s set_npe %s %s' % (self.__model, self.__name, self.__npe))

    def __getnpe(self):
        """ Returns npe property
        """
        return self.__npe

    npe = property(__getnpe, __setnpe, doc = 'The npe property of this router')


    def __setmidplane(self, midplane):
        """ Set the midplane property
            midplane: (string) Set the midplane type
        """
        if type(midplane) != str or midplane not in ['std', 'vxr']:
            raise DynamipsError('invalid midplane type')
        self.__midplane = midplane
        send(self.__d, '%s set_midplane %s %s' % (self.__model, self.__name, self.__midplane))

    def __getmidplane(self):
        """ Returns midplane property
        """
        return self.__midplane

    midplane = property(__getmidplane, __setmidplane, doc = 'The midplane property of this router')


    def __setnvram(self, nvram):
        """ Set amount of nvram allocated to this router
            nvram: (int) amount of nvram in KB
        """
        if type(nvram) != int or nvram < 1:
            raise DynamipsError('invalid nvram size')
        self.__nvram = nvram
        send(self.__d, 'vm set_nvram %s %i' % (self.__name, self.__nvram))

    def __getnvram(self):
        """ Returns the amount of nvram allocated to this router
        """
        return self.__nvram

    nvram = property(__getnvram, __setnvram, doc = 'The amount of nvram allocated to this router')


    def __setimage(self, image):
        """ Set the IOS image for this router
            image: path to IOS image file
        """
        self.__image = image
        # Can't verify existance of image because path is relative to backend
        send(self.__d, 'vm set_ios %s %s' % (self.__name, self.__image))

    def __getimage(self):
        """ Returns path of the image being used by this router
        """
        return self.__image

    image = property(__getimage, __setimage, doc = 'The IOS image file for this router')


    def __getimagename(self):
        """ Returns just the name of the image file used
        """
        if self.__image == None:
            return None
        image = os.path.basename(self.__image).strip('"')
        return image

    imagename = property(__getimagename, doc = 'The name of the IOS image file for this router')


    def __setcnfg(self, cnfg):
        """ Import an IOS configuration file into NVRAM
            cnfg: path to configuration file to be imported
        """
        self.__cnfg = cnfg
        # Can't verify existance of cnfg because path is relative to backend
        send(self.__d, 'vm set_config %s %s' % (self.__name, self.__cnfg))

    def __getcnfg(self):
        """ Returns path of the cnfg being used by this router
        """
        return self.__cnfg

    cnfg = property(__getcnfg, __setcnfg, doc = 'The IOS configuration file to import into NVRAM')


    def __setconfreg(self, confreg):
        """ Set the configuration register
            confreg: confreg string
        """
        self.__confreg = confreg
        send(self.__d, 'vm set_conf_reg %s %s' % (self.__name, self.__confreg))

    def __getconfreg(self):
        """ Returns the confreg
        """
        return self.__confreg

    confreg = property(__getconfreg, __setconfreg, doc = 'The configuration register of this router')

    def __set_config_b64(self, conf64):
        """ Set the config to this base64 encoded configuration"""

        if DEBUGGER: return         # Work around an annoying bug in the Komodo debugger
        send(self.__d, 'vm push_config %s %s' % (self.__name, conf64))

    def __get_config_b64(self):
        """Get the base64 encoded config from the router's nvram"""

        if DEBUGGER: return         # Work around an annoying bug in the Komodo debugger
        cf = send(self.__d, 'vm extract_config %s' % (self.__name))
        b64config = cf[0].split(' ')[2].strip()
        return b64config

    config_b64 = property(__get_config_b64, __set_config_b64, doc = 'The configuration of this router in base64 encoding')


    def __setidlepc(self, pc):
        """ Set the Idle Pointer Counter for this instance
            pc: idle-pc string
        """
        self.__idlepc = pc
        send(self.__d, 'vm set_idle_pc %s %s' % (self.__name, self.__idlepc))

    def __getidlepc(self):
        """ Returns the current idlepc
        """
        return self.__idlepc

    idlepc = property(__getidlepc, __setidlepc, doc = 'The Idle Pointer Counter assigned to this instance')

    def __getidlepcdrift(self):
        """ Returns the current idlepcdrift
        """
        result = send(self.__d, 'vm show_timer_drift %s 0' % (self.__name))
        if result[-1] == '100-OK': result.pop()
        return result

    idlepcdrift = property(__getidlepcdrift, doc = 'The idle-pc drift valueof instance')

    def __setidlemax(self, val):
        """ Set the idlemax value for this instance
            val: (integer) idlemax counter
        """
        self.__idlemax = val
        send(self.__d, 'vm set_idle_max %s 0 %i' % (self.__name, self.__idlemax))

    def __getidlemax(self):
        """ Returns the current idlemax
        """
        return self.__idlemax

    idlemax = property(__getidlemax, __setidlemax, doc = 'The Idle Pointer Counter assigned to this instance')

    def __setidlesleep(self, val):
        """ Set the idle_sleep_time for this instance
            val: (integer) sleep time in ms
        """
        self.__idlesleep = val
        send(self.__d, 'vm set_idle_sleep_time %s 0 %i' % (self.__name, self.__idlesleep))

    def __getidlesleep(self):
        """ Returns the current idlesleep value for this instance
        """
        return self.__idlesleep

    idlesleep = property(__getidlesleep, __setidlesleep, doc = 'The idle sleep time of this instance')

    def __setexec_area(self, exec_area):
        """ Set the Exec Area size for this instance
            pc: Exec area integer
        """
        self.__exec_area = exec_area
        send(self.__d, 'vm set_exec_area %s %s' % (self.__name, str(self.__exec_area)))

    def __getexec_area(self):
        """ Returns the exec_area
        """
        return self.__exec_area

    exec_area = property(__getexec_area, __setexec_area, doc = 'The Exec Area size assigned to this instance')


    def __setghost_status(self, status):
        """ Set the ghost_status of this instance
            status: (int) Tristate flag indicating status
                    0 -> Do not use IOS ghosting
                    1 -> This is a ghost instance
                    2 -> Use an existing ghost instance
        """
        self.__ghost_status = status
        send(self.__d, 'vm set_ghost_status %s %s' % (self.__name, str(self.__ghost_status)))

    def __getghost_status(self):
        """ Returns the ghost_status
        """
        return self.__ghost_status

    ghost_status = property(__getghost_status, __setghost_status, doc = 'The ghost status of this instance')

    def __setghost_file(self, ghost_file):
        """ Set the ghost file for this instance
            ghost_file: (string) ghost file name to create (or reference)
        """
        self.__ghost_file = ghost_file
        send(self.__d, 'vm set_ghost_file %s %s' % (self.__name, str(self.__ghost_file)))

    def __getghost_file(self):
        """ Returns the ghost_file
        """
        return self.__ghost_file

    ghost_file = property(__getghost_file, __setghost_file, doc = 'The ghost file associated with this instance')


    def __getdynamips(self):
        """ Returns the dynamips server on which this device resides
        """
        return self.__d

    dynamips = property(__getdynamips, doc = 'The dynamips object associated with this device')


    def __getmodel(self):
        """ Returns model of this router
        """
        return self.__model

    model = property(__getmodel, doc = 'The model of this router')


    def __getname(self):
        """ Returns the name of this router
        """
        return self.__name

    name = property(__getname, doc = 'The name of this router')

    def __getstate(self):
        """ Returns the state of this router
        """
        return self.__state

    state = property(__getstate, doc = 'The state of this router')

    def __getisrouter(self):
        """ Returns true if this device is a router
        """
        return True

    isrouter = property(__getisrouter, doc = 'Returns true if this device is a router')


class C7200(Router):
    """ Creates a new 7200 Router instance
        dynamips: a Dynamips object
        console (optional): TCP port that attaches to this router's console.
                            Defaults to TCP 2000 + the instance number
        name (optional): An optional name. Defaults to the instance number
    """

    def __init__(self, dynamips, name = None):
        Router.__init__(self, dynamips, model = 'c7200', name = name)
        # Set defaults for properties
        Router.setdefaults(self,
        ram = 256,
        nvram = 128,
        disk0 = 64,
        disk1 = 0,
        npe = "npe-200",
        midplane = "vxr")

        # generate the slots for port adapters
        Router.createslots(self, 7)

class C2691(Router):
    """ Creates a new 2691 Router instance
        dynamips: a Dynamips object
        console (optional): TCP port that attaches to this router's console.
                            Defaults to TCP 2000 + the instance number
        name (optional): An optional name. Defaults to the instance number
    """

    def __init__(self, dynamips, name = None):
        Router.__init__(self, dynamips, model = 'c2691', name = name)
        # Set defaults for properties
        Router.setdefaults(self,
        ram = 128,
        nvram = 55,
        disk0 = 16,
        disk1 = 0)

        # generate the slots for network modules
        Router.createslots(self, 2)

class C3725(Router):
    """ Creates a new 3725 Router instance
        dynamips: a Dynamips object
        console (optional): TCP port that attaches to this router's console.
                            Defaults to TCP 2000 + the instance number
        name (optional): An optional name. Defaults to the instance number
    """

    def __init__(self, dynamips, name = None):
        Router.__init__(self, dynamips, model = 'c3725', name = name)
        # Set defaults for properties
        Router.setdefaults(self,
        ram = 128,
        nvram = 55,
        disk0 = 16,
        disk1 = 0)

        # generate the slots for network modules
        Router.createslots(self, 3)

class C3745(Router):
    """ Creates a new 3745 Router instance
        dynamips: a Dynamips object
        console (optional): TCP port that attaches to this router's console.
                            Defaults to TCP 2000 + the instance number
        name (optional): An optional name. Defaults to the instance number
    """

    def __init__(self, dynamips, name = None):
        Router.__init__(self, dynamips, model = 'c3745', name = name)
        # Set defaults for properties
        Router.setdefaults(self,
        ram = 128,
        nvram = 151,
        disk0 = 16,
        disk1 = 0)

        # generate the slots for network modules
        Router.createslots(self, 5)


class C3600(Router):
    """ Creates a new 3620 Router instance
        dynamips: a Dynamips object
        console (optional): TCP port that attaches to this router's console.
                            Defaults to TCP 2000 + the instance number
        name (optional): An optional name. Defaults to the instance number
    """

    def __init__(self, dynamips, chassis, name = None):
        self.__d = dynamips
        self.__chassis = chassis
        self.__name = name

        Router.__init__(self, dynamips, model = 'c3600', name = name)
        # Set defaults for properties
        Router.setdefaults(self,
        ram = 128,
        nvram = 128,
        disk0 = 0,
        disk1 = 0)

        self.chassis = chassis

        # generate the slots for port adapters
        if chassis == '3620':
            Router.createslots(self, 2)
        elif chassis == '3640':
            Router.createslots(self, 4)
        elif chassis == '3660':
            Router.createslots(self, 7)
        else:
            debug("Unable to match chassis type. Chassis -> " + str(chassis))
            raise DynamipsError('invalid chassis type')

    def __setchassis(self, chassis):
        """ Set the chassis property
            chassis: (string) Set the chassis type
        """
        if type(chassis) not in [str, unicode] or chassis not in ['3620', '3640', '3660']:
            debug("Invalid chassis passed to __setchassis")
            debug("chassis -> '" + str(chassis) +"'")
            debug("chassis type -> " + str(type(chassis)))
            raise DynamipsError('invalid chassis type')
        self.__chassis = chassis
        send(self.__d, 'c3600 set_chassis %s %s' % (self.__name, self.__chassis))

    def __getchassis(self):
        """ Returns chassis property
        """
        return self.__chassis

    chassis = property(__getchassis, __setchassis, doc = 'The chassis property of this router')


    def __setiomem(self, iomem):
        """ Set the iomem property
            iomem: (string) Set the iomem value
        """
        try:
            iomem = int(iomem)
        except ValueError:
            raise DynamipsError('invalid iomem type, must be an integer')
        if iomem % 5 != 0:
            raise DynamipsError('iomem must be a multiple of 5')
        self.__iomem = iomem
        send(self.__d, 'c3600 set_iomem %s %s' % (self.__name, self.__iomem))

    def __getiomem(self):
        """ Returns iomem property
        """
        return self.__iomem

    iomem = property(__getiomem, __setiomem, doc = 'The iomem size of this router')

class DynamipsError(Exception):
    pass

class DynamipsWarning(Exception):
    pass

###############################################################################

class Bridge(object):
    """ Creates a new Ethernet bridge instance
        dynamips: a Dynamips object
        name: An optional name
    """
    __instance_count = 0

    def __init__(self, dynamips, name = None, create = True):
        self.__d = dynamips
        self.__instance = Bridge.__instance_count
        Bridge.__instance_count += 1
        if name == None:
            self.__name = 'b' + str(self.__instance)
        else:
            self.__name = name

        self.__nios = []    # A list NETIO objects that are associated with this bridge

        if create:
            send(self.__d, "nio_bridge create " + self.__name)

    def delete(self):
        """ Delete this Frame Relay switch instance from the back end
        """
        pass


    def nio(self, nio = None):
        """ Adds an NIO to this bridge
            nio: A nio object
        """
        if nio == None:
            # Return the NETIO string
            try:
                return self.__nios
            except KeyError:
                raise DynamipsError('port does not exist on this switch')

        nio_t = type(nio)
        if nio_t == NIO_udp or nio_t == NIO_linux_eth or nio_t == NIO_gen_eth or nio_t == NIO_tap or nio_t == NIO_unix:
            send(self.__d, 'nio_bridge add_nio %s %s' % (self.__name, nio.name))

        # Add the NETIO to the list
        self.__nios.append(nio)


    def __getadapter(self):
        """ Returns the adapter property
        """
        return "Bridge"

    adapter = property(__getadapter, doc = 'The port adapter')

    def __getname(self):
        """ Returns the name property
        """
        return self.__name

    name = property(__getname, doc = 'The device name')


    def __getdynamips(self):
        """ Returns the dynamips server on which this device resides
        """
        return self.__d

    dynamips = property(__getdynamips, doc = 'The dynamips object associated with this device')

    def __getisrouter(self):
        """ Returns true if this device is a router
        """
        return False

    isrouter = property(__getisrouter, doc = 'Returns true if this device is a router')

########################################################################################
class FRSW(object):
    """ Creates a new Frame Relay switch instance
        dynamips: a Dynamips object
        name: An optional name
    """
    __instance_count = 0

    def __init__(self, dynamips, name = None, create = True):
        self.__d = dynamips
        self.__instance = FRSW.__instance_count
        FRSW.__instance_count += 1
        if name == None:
            self.__name = 'f' + str(self.__instance)
        else:
            self.__name = name

        self.__dlcis = {}   # A dict of DLCIs (tuple) indexed by switch port
        self.__nios = {}    # A dict of NETIO objects indexed by switch port

        if create:
            send(self.__d, "frsw create " + self.__name)

    def delete(self):
        """ Delete this Frame Relay switch instance from the back end
        """
        pass


    def map(self, port1, dlci1, port2, dlci2):
        """ Tell the switch to switch between port1 / dlci1 and port 2 / dlci2
            NOTE: both ports must be connected to something before map can be applied
            port1, port2: Two different ports on this switch
            dlci1, dlci2: DLCIs assigned to the respective ports on this switch
        """
        # Also note: if you change connections you need to reapply maps that
        # are associated with those ports

        if type(port1) != int or port1 < 0:
            raise DynamipsError('invalid port1. Must be an int >= 0')
        if type(port2) != int or port2 < 0:
            raise DynamipsError('invalid port2. Must be an int >= 0')
        if type(dlci1) != int or dlci1 < 0:
            raise DynamipsError('invalid dlci1. Must be an int >= 0')
        if type(dlci2) != int or dlci2 < 0:
            raise DynamipsError('invalid dlci1. Must be an int >= 0')

        try:
            nio1 = self.nio(port1).name
        except KeyError:
            raise DynamipsError('port1 does not exist on this switch')
        try:
            nio2 = self.nio(port2).name
        except KeyError:
            raise DynamipsError('port2 does not exist on this switch')

        send(self.__d, 'frsw create_vc %s %s %i %s %i' % (self.__name, nio1, dlci1, nio2, dlci2))

        # Now track the dlcis
        if self.__dlcis.has_key(port1):
            self.__dlcis[port1].append(dlci1)
        else:
            self.__dlcis[port1] = [dlci1]
        if self.__dlcis.has_key(port2):
            self.__dlcis[port2].append(dlci2)
        else:
            self.__dlcis[port2] = [dlci2]


    def connect(self, localport, remoteserver, remoteadapter, remoteport):
        """ Connect this switch to a port on another device
            remoteserver: the dynamips object that hosts the remote adapter
            remoteadapter: An adapter object on a router
            remoteport: A port on the remote adapter
        """
        # Call the generalized connect function
        gen_connect(src_dynamips = self.__d,
                    src_adapter = self,
                    src_port = localport,
                    dst_dynamips = remoteserver,
                    dst_adapter = remoteadapter,
                    dst_port = remoteport)


    def connected(self, port):
        """ Returns a boolean indicating if this port is connected or not
        """
        return connected_general(self, port)


    def nio(self, port, nio = None):
        """ Returns the NETIO object for this port
            or if nio is set, sets the NETIO for this port
            port: a port on this adapter
            nio: optional NETIO object to assign
        """
        if nio == None:
            # Return the NETIO string
            try:
                return self.__nios[port]
            except KeyError:
                raise DynamipsWarning('Frame-Relay switchport ' + str(port) + ' on device "' + self.name + '" is defined, but not used')


        # as of 0.2.5pre5 add_nio has been removed. For now I'm just removing sending the nio command
        #nio_t = type(nio)
        # is is kosher to connect a frame relay switch to a linux or gen interface? I don't know... How about chained FRSW switches?
        #if nio_t == NIO_udp or nio_t == NIO_linux_eth or nio_t == NIO_gen_eth or nio_t == NIO_tap or nio_t == NIO_unix:
        #    send(self.__d, 'frsw add_nio %s %s' % (self.__name, nio.name))

        # Set the NETIO for this port
        self.__nios[port] = nio




    def dlci(self, port):
        """ Returns the DLCIs assigned to this port (as a list)
            port: (int) a port on this switch
            dlcis: one or more DLCIs
        """
        # Return the DLCIs assigned to this port
        try:
            return self.__dlcis[port]
        except KeyError:
            raise DynamipsError('invalid port')


    def __getadapter(self):
        """ Returns the adapter property
        """
        return "FRSW"

    adapter = property(__getadapter, doc = 'The port adapter')


    def __getname(self):
        """ Returns the name property
        """
        return self.__name

    name = property(__getname, doc = 'The device name')


    def __getdynamips(self):
        """ Returns the dynamips server on which this device resides
        """
        return self.__d

    dynamips = property(__getdynamips, doc = 'The dynamips object associated with this device')

    def __getisrouter(self):
        """ Returns true if this device is a router
        """
        return False

    isrouter = property(__getisrouter, doc = 'Returns true if this device is a router')


###############################################################################

class ATMSW(object):
    """ Creates a new ATM switch instance
        dynamips: a Dynamips object
        name: An optional name
    """
    __instance_count = 0

    def __init__(self, dynamips, name = None, create = True):
        self.__d = dynamips
        self.__instance = ATMSW.__instance_count
        ATMSW.__instance_count += 1
        if name == None:
            self.__name = 'a' + str(self.__instance)
        else:
            self.__name = name

        self.__vpis = {}   # A dict of vpis (tuple) indexed by switch port
        self.__nios = {}    # A dict of NETIO objects indexed by switch port

        if create:
            send(self.__d, "atmsw create " + self.__name)

    def delete(self):
        """ Delete this ATM switch instance from the back end
        """
        pass


    def mapvp(self, port1, vpi1, port2, vpi2):
        """ Tell the switch to switch between port1 / vpi1 and port 2 / vpi2
            NOTE: both ports must be connected to something before map can be applied
            port1, port2: Two different ports on this switch
            vpi1, vpi2: vpis assigned to the respective ports on this switch
        """
        # Also note: if you change connections you need to reapply maps that
        # are associated with those ports

        if type(port1) != int or port1 < 0:
            raise DynamipsError('invalid port1. Must be an int >= 0')
        if type(port2) != int or port2 < 0:
            raise DynamipsError('invalid port2. Must be an int >= 0')
        if type(vpi1) != int or vpi1 < 0:
            raise DynamipsError('invalid vpi1. Must be an int >= 0')
        if type(vpi2) != int or vpi2 < 0:
            raise DynamipsError('invalid vpi2. Must be an int >= 0')

        try:
            nio1 = self.nio(port1).name
        except KeyError:
            raise DynamipsError('port1 does not exist on this switch')
        try:
            nio2 = self.nio(port2).name
        except KeyError:
            raise DynamipsError('port2 does not exist on this switch')

        send(self.__d, 'atmsw create_vpc %s %s %i %s %i' % (self.__name, nio1, vpi1, nio2, vpi2))

        # Now track the vpis
        if self.__vpis.has_key(port1):
            self.__vpis[port1].append(vpi1)
        else:
            self.__vpis[port1] = [vpi1]
        if self.__vpis.has_key(port2):
            self.__vpis[port2].append(vpi2)
        else:
            self.__vpis[port2] = [vpi2]

    def mapvc(self, port1, vpi1, vci1, port2, vpi2, vci2):
        """ Tell the switch to switch between port1 / vpi1 / vci1 and port 2 / vpi2 / vci2
            NOTE: both ports must be connected to something before map can be applied
            port1, port2: Two different ports on this switch
            vpi1, vpi2: vpis assigned to the respective ports on this switch
            vci1, vci2: vcis
        """
        # Also note: if you change connections you need to reapply maps that
        # are associated with those ports

        if type(port1) != int or port1 < 0:
            raise DynamipsError('invalid port1. Must be an int >= 0')
        if type(port2) != int or port2 < 0:
            raise DynamipsError('invalid port2. Must be an int >= 0')
        if type(vpi1) != int or vpi1 < 0:
            raise DynamipsError('invalid vpi1. Must be an int >= 0')
        if type(vpi2) != int or vpi2 < 0:
            raise DynamipsError('invalid vpi2. Must be an int >= 0')
        if type(vci1) != int or vci1 < 0:
            raise DynamipsError('invalid vci1. Must be an int >= 0')
        if type(vci2) != int or vci2 < 0:
            raise DynamipsError('invalid vci2. Must be an int >= 0')

        try:
            nio1 = self.nio(port1).name
        except KeyError:
            raise DynamipsError('port1 does not exist on this switch')
        try:
            nio2 = self.nio(port2).name
        except KeyError:
            raise DynamipsError('port2 does not exist on this switch')

        send(self.__d, 'atmsw create_vcc %s %s %i %i %s %i %i' % (self.__name, nio1, vpi1, vci1, nio2, vpi2, vci2))

        # Now track the vpis
        if self.__vpis.has_key(port1):
            self.__vpis[port1].append(vpi1)
        else:
            self.__vpis[port1] = [vpi1]
        if self.__vpis.has_key(port2):
            self.__vpis[port2].append(vpi2)
        else:
            self.__vpis[port2] = [vpi2]

    def connect(self, localport, remoteserver, remoteadapter, remoteport):
        """ Connect this switch to a port on another device
            remoteserver: the dynamips object that hosts the remote adapter
            remoteadapter: An adapter object on a router
            remoteport: A port on the remote adapter
        """
        # Call the generalized connect function
        gen_connect(src_dynamips = self.__d,
                    src_adapter = self,
                    src_port = localport,
                    dst_dynamips = remoteserver,
                    dst_adapter = remoteadapter,
                    dst_port = remoteport)


    def connected(self, port):
        """ Returns a boolean indicating if this port is connected or not
        """
        return connected_general(self, port)


    def nio(self, port, nio = None):
        """ Returns the NETIO object for this port
            or if nio is set, sets the NETIO for this port
            port: a port on this adapter
            nio: optional NETIO object to assign
        """
        if nio == None:
            # Return the NETIO string
            try:
                return self.__nios[port]
            except KeyError:
                raise DynamipsWarning('ATM switchport ' + str(port) + ' on device "' + self.name + '" is defined, but not used')


        # as of 0.2.5pre5 add_nio has been removed. For now I'm just removing sending the nio command
        #nio_t = type(nio)
        # is is kosher to connect an ATM switch to a linux or gen interface? I don't know... How about chained ATM switches?
        #if nio_t == NIO_udp or nio_t == NIO_linux_eth or nio_t == NIO_gen_eth or nio_t == NIO_tap or nio_t == NIO_unix:
        #    send(self.__d, 'atmsw add_nio %s %s' % (self.__name, nio.name))

        # Set the NETIO for this port
        self.__nios[port] = nio


    def vpi(self, port):
        """ Returns the vpis assigned to this port (as a list)
            port: (int) a port on this switch
            vpis: one or more vpis
        """
        # Return the vpis assigned to this port
        try:
            return self.__vpis[port]
        except KeyError:
            raise DynamipsError('invalid port')


    def __getadapter(self):
        """ Returns the adapter property
        """
        return "ATMSW"

    adapter = property(__getadapter, doc = 'The port adapter')


    def __getname(self):
        """ Returns the name property
        """
        return self.__name

    name = property(__getname, doc = 'The device name')


    def __getdynamips(self):
        """ Returns the dynamips server on which this device resides
        """
        return self.__d

    dynamips = property(__getdynamips, doc = 'The dynamips object associated with this device')

    def __getisrouter(self):
        """ Returns true if this device is a router
        """
        return False

    isrouter = property(__getisrouter, doc = 'Returns true if this device is a router')


###############################################################################

class ETHSW(object):
    """ Creates a new Ethernet switch instance
        dynamips: a Dynamips object
        name: An optional name
    """
    __instance_count = 0

    def __init__(self, dynamips, name = None, create = True):
        self.__d = dynamips
        self.__instance = ETHSW.__instance_count
        ETHSW.__instance_count += 1
        if name == None:
            self.__name = 's' + str(self.__instance)
        else:
            self.__name = name

        #self.__dlcis = {}   # A dict of DLCIs (tuple) indexed by switch port
        self.__nios = {}    # A dict of NETIO objects indexed by switch port

        if create:
            send(self.__d, "ethsw create " + self.__name)

    def delete(self):
        """ Delete this Frame Relay switch instance from the back end
        """
        pass


    def set_port(self, port, porttype, vlan):
        """ Define a port as an access port or trunk port, and it's vlan
            port: the switchport
            porttype: string of the value "access" or "dot1q"
            vlan: the vlan
        """

        if type(port) != int:
            raise DynamipsError('invalid port. Must be an int >= 0')
        if type(vlan) != int:
            raise DynamipsError('invalid vlan. Must be an int >= 0')
        try:
            nio = self.nio(port).name
        except KeyError:
            raise DynamipsError('port1 does not exist on this switch')

        porttype = porttype.lower()
        if porttype != 'access' and porttype != 'dot1q':
            raise DynamipsError('invalid porttype')

        send(self.__d, "ethsw set_" + porttype + "_port " + self.__name + " " + nio + " " + str(vlan))


    def show_mac(self):
        """ Show this switch's mac address table
        """
        return send(self.__d, "ethsw show_mac_addr_table " + self.__name)


    def clear_mac(self):
        """ Clear this switch's mac address table
        """
        return send(self.__d, "ethsw clear_mac_addr_table " + self.__name)

    def connect(self, localport, remoteserver, remoteadapter, remoteport):
        """ Connect this switch to a port on another device
            remoteserver: the dynamips object that hosts the remote adapter
            remoteadapter: An adapter object on a router
            remoteport: A port on the remote adapter
        """
        # Call the generalized connect function
        gen_connect(src_dynamips = self.__d,
                    src_adapter = self,
                    src_port = localport,
                    dst_dynamips = remoteserver,
                    dst_adapter = remoteadapter,
                    dst_port = remoteport)


    def connected(self, port):
        """ Returns a boolean indicating if this port is connected or not
        """
        return connected_general(self, port)


    def nio(self, port, nio = None, porttype = None, vlan = None):
        """ Returns the NETIO object for this port
            or if nio is set, sets the NETIO for this port
            port: a port on this adapter
            nio: optional NETIO object to assign
            porttype: either access or dot1q
        """
        if nio == None:
            # Return the NETIO string
            try:
                return self.__nios[port]
            except KeyError:
                raise DynamipsWarning('Ethernet switchport ' + str(port) + ' on device "' + self.name + '" is defined, but not used')

        nio_t = type(nio)
        if nio_t == NIO_udp or nio_t == NIO_linux_eth or nio_t == NIO_gen_eth or nio_t == NIO_tap or nio_t == NIO_unix:
            send(self.__d, 'ethsw add_nio %s %s' % (self.__name, nio.name))
        else:
            raise DynamipsError('invalid NIO type')

        # Set the NETIO for this port
        self.__nios[port] = nio
        if porttype != None:
            porttype = porttype.lower()
            if porttype != 'access' and porttype != 'dot1q':
                raise DynamipsError('invalid porttype')

            send(self.__d, "ethsw set_" + porttype + "_port " + self.__name + " " + nio.name + " " + str(vlan))


    def __getadapter(self):
        """ Returns the adapter property
        """
        return "ETHSW"

    adapter = property(__getadapter, doc = 'The port adapter')


    def __getname(self):
        """ Returns the name property
        """
        return self.__name

    name = property(__getname, doc = 'The device name')


    def __getdynamips(self):
        """ Returns the dynamips server on which this device resides
        """
        return self.__d

    dynamips = property(__getdynamips, doc = 'The dynamips object associated with this device')

    def __getisrouter(self):
        """ Returns true if this device is a router
        """
        return False

    isrouter = property(__getisrouter, doc = 'Returns true if this device is a router')


###############################################################################

# Functions used by all classes
def send(dynamips, command):
    """ Sends raw commands to the Dynamips process
        dynamips: a dynamips object
        command: raw commands

        returns results as a list
    """

    # Dynamips responses are of the form:
    #   1xx yyyyyy\r\n
    #   1xx yyyyyy\r\n
    #   ...
    #   100-yyyy\r\n
    # or
    #   2xx-yyyy\r\n
    #
    # Where 1xx is a code from 100-199 for a sucess or 200-299 for an error
    # The result might be multiple lines, and might be less than the buffer size
    # but still have more data. The only thing we know for sure is the last line
    # will begin with "100-" or a "2xx-" and end with '\r\n'

    SIZE = 1024         # Match to Dynamips' buffer size
    resultset = []

    debug('sending to ' + dynamips.host + ':' + str(dynamips.port) + ' -> ' + command)
    if not NOSEND:
        try:
            dynamips.s.sendall(command.strip() + '\n')
        except:
            print("Error: lost communication with dynamips server %s" % dynamips.host)
            #sys.exit(1)

        # Now retrieve the result
        data = []
        buf = ''
        while True:
            try:
                chunk = dynamips.s.recv(SIZE)
                #debug('Chunk: ' + chunk)
                buf += chunk
            except timeout as message:
                print("Error: timed out communicating with dynamips server %s" % dynamips.host)
                print(message)
                raise DynamipsError("timeout")

            # if the buffer doesn't end in '\n' then we can't be done
            if buf[-1] != '\n':
                continue

            data += buf.split('\r\n')
            if data[-1] == '': data.pop()
            buf = ''

            # Does the last line begin with "100-"? Then we are done:
            if data[-1][:4] == '100-':
                break

            # Or does it contain an error code?
            if error_re.search(data[-1]):
                raise DynamipsError(data[-1])

            # Otherwise loop throught again and get the the next line of data

        if len(data) == 0:
            print("Error: no data returned from dynamips server %s. Server crashed?" % dynamips.host)
            raise DynamipsError("no data")

        debug('returned -> ' + str(data))

        return data
    else:
        return ''       # NOSEND, so return empty string

def gen_connect(src_dynamips, src_adapter, src_port, dst_dynamips, dst_adapter, dst_port):
    """ Generalized connect function called by all connect methods. Connects a souce interface / port to
        a destination interface / port
        src_dynamips: the dynamips object that hosts the source connection
        src_adapter: the source adapter
        src_port: the source port
        dst_dynamips: the dynamips object that hosts the destination connection
        dst_adapter: the destination adatper
        dst_port: the destination port (set to none if the destination is a bridge)
    """

    # Can the source adapter be connected to the destination adapter?
    validate_connect(src_adapter, dst_adapter)

    if src_dynamips.host == dst_dynamips.host:
        # source and dest adapters are on the same dynamips server, perform loopback binding optimization
        src_ip = '127.0.0.1'
        dst_ip = '127.0.0.1'
    else:
        # source and dest are on different dynamips servers
        src_ip = src_dynamips.host
        dst_ip = dst_dynamips.host

    # Dynagen connect currently always uses UDP NETIO
    # Allocate a UDP port for the local side of the NIO
    src_udp = src_dynamips.udp
    src_dynamips.udp = src_dynamips.udp + 1
    debug("source NIO udp is now: " + str(src_dynamips.udp))

    # Now allocate one for the destination side
    dst_udp = dst_dynamips.udp
    dst_dynamips.udp = dst_dynamips.udp + 1
    debug ("dest NIO udp is now: " + str(dst_dynamips.udp))

    # Create the NIOs
    src_nio = NIO_udp(src_dynamips, src_udp, dst_ip, dst_udp)
    dst_nio = NIO_udp(dst_dynamips, dst_udp, src_ip, src_udp)

    # Tie the NIOs to the source and destination ports / bridges
    src_adapter.nio(port=src_port, nio=src_nio)
    if isinstance(dst_adapter, Bridge):
        # Bridges don't use ports
        dst_adapter.nio(nio=dst_nio)
    else:
        dst_adapter.nio(port=dst_port, nio=dst_nio)


def validate_connect(int1, int2):
    """ Check to see if a given adapter can be connected to another adapter
        int1: Interface 1
        int2: Interface 2
    """
    try:
        a1 = int1.adapter
        a2 = int2.adapter
    except AttributeError:
        raise DynamipsError('invalid adapter or no adapter present')

    # Question: can we daisy-chain switches? Validate this.
    ethernets = ('C7200-IO-FE', 'PA-FE-TX', 'PA-4E', 'PA-8E', 'NM-1FE-TX', 'NM-1E', 'NM-4E', 'NM-16ESW', 'Leopard-2FE', 'GT96100-FE', 'Bridge', 'ETHSW')
    serials = ('PA-4T+', 'PA-8T', 'NM-4T', 'FRSW')
    atms = ('PA-A1', 'ATMSW')
    poss = ('PA-POS-OC3')

    if a1 == 'Bridge' and a2 == 'Bridge':
        raise DynamipsError('attempt to connect two bridges')

    if a1 in ethernets and a2 in ethernets:
        return

    elif a1 in serials and a2 in serials:
        return

    elif a1 in atms and a2 in atms:
        return

    elif a1 in poss and a2 in poss:
        return

    else:
        raise DynamipsError('attempt to connect %s to %s' % (a1, a2))


def connected_general(obj, port):
    """ Returns a boolean indicating if this port is connected or not
    """
    # If it's got an nio, I guess it's connected
    try:
        nio1 = obj.nio(port).name
    except AttributeError:
        return False
    return True


def checkconsole(console, dynamips):
    """ Returns the device that uses the console port
        Returns None if no device has that console port
    """
    # Hunt through the console ports in use to see if there is a conflict
    for device in dynamips.devices:
        try:
            con2 = device.console
        except AttributeError:
            # This device has no console value
            continue
        if console == con2:
            return device
    return None


def nosend(flag):
    """ If true, don't actually send any commands to the back end.
    """
    global NOSEND
    if flag == True or flag == False:
        NOSEND = flag


def setdebug(flag):
    """ If true, print out debugs
    """
    global DEBUG

    if flag == True or flag == False:
        DEBUG = flag


def debug(string):
    """ Print string if debugging is true
    """
    global DEBUG

    if DEBUG: print('  DEBUG: ' + str(string))


if __name__ == "__main__":
    # Testing
    DEBUG = True

    #IMAGE = '/opt/3620-images/c3620-io3-mz.123-20.image'
    #IMAGE = '/opt/3640-images/c3640-ik9o3s-mz.124-8a.image'
    IMAGE = '/opt/3660-images/c3660-ik9o3s-mz.124-10.image'
    #IMAGE2 = '/opt/7200-images/c7200-ik9o3s-mz.124-5a.image'
    d = Dynamips('bender', 7200)
    d.reset()
    d.workingdir = '/home/greg/labs/tests/NM-16ESW'

    r1 = C3600(d, chassis = '3660', name='r1')
    esw = C3600(d, chassis = '3660', name='esw')
    r1.image = IMAGE
    esw.image = IMAGE
    r1.slot[0] = Leopard_2FE(r1,0)
    esw.slot[1] = NM_16ESW(esw, 1)
    r1.idlepc = '0x605b83f4'
    esw.idlepc = '0x605b83f4'
    r1.slot[0].connect(0, d, esw.slot[1], 0)

    r1.start()
    esw.start()

    d.reset()

    #print r1.ram
    #print d.version
    #r1.iomem = 50
    #d.reset()

    """
    d.workingdir = '/home/greg/labs/lib-3660'

    r1 = C3600(d, chassis = '3620', name='r1')
    #print r1.ram
    r1.image = IMAGE

    #r2 = C3600(d, chassis = '3640', name='r2')
    #r2.image = IMAGE

    #r1.slot[0] = Leopard_2FE(r1, 0)
    r1.slot[1] = NM_1FE_TX(r1,1)
    #r2.slot[0] = NM_1FE_TX(r2, 0)

    r2 = C7200(d, name='r2')
    r2.image = IMAGE2

    #b1 = Bridge(d)

    #r1.slot[0].connect(0, d, b1)
    r2.slot[0] = PA_C7200_IO_FE(r2, 0)
    #r2.slot[0].connect(0, d, b1)

    r1.slot[1].connect(0, d, r2.slot[0], 0)

    r1.start()
    r2.start()

    d.reset()

    IMAGE = '/opt/7200-images/c7200-ik9o3s-mz.124-5a.image'
    d = Dynamips('bender', 7200)
    d.reset()

    d.workingdir = '/home/greg/labs/lib-3600'

    r1 = C7200(d, name='r1')
    print r1.ram

    r1.image = IMAGE
    r2 = C7200(d, name='r2')
    r2.image = IMAGE

    r1.slot[0] = PA_C7200_IO_FE(r1, 0)
    r2.slot[0] = PA_C7200_IO_FE(r2, 0)

    b1 = Bridge(d)

    r1.slot[0].connect(0, d, b1)
    r2.slot[0].connect(0, d, b1)


    r1.start()
    r2.start()

    d.reset()
    """

