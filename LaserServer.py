import socket

from Kernel import *


class LaserServer(Module):
    """
    Laser Server opens up a localhost server and waits, sends whatever data received to the pipe
    """
    def __init__(self, tcp=True, port=23, pipe=None, name=''):  # port 1040
        Module.__init__(self)
        self.tcp = tcp
        self.pipe = pipe
        self.port = port
        self.name = name

        self.socket = None
        self.channel = lambda e: e
        self.connection = None
        self.addr = None

        self.elems = None
        self.reply = None

    def initialize(self):
        if self.tcp:
            self.socket = socket.socket()
            self.socket.bind(('', self.port))
            self.socket.listen(1)
            self.device.threaded(self.tcp_run)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('', self.port))
            self.device.threaded(self.udp_run)
        self.device.control_instance_add('Set_Server_Pipe' + self.name, self.set_pipe)
        self.channel = self.device.channel_open('server')

    def udp_run(self):
        try:
            reply = lambda e: self.socket.sendto(e, address)
            elems = lambda e: self.device.device_root.elements.add_elem(e)
            while True:
                message, address = self.socket.recvfrom(1024)
                self.pipe.checksum_parse(message, reply=reply, elements=elems)
        except OSError:
            pass

    def tcp_run(self):
        def reply(e):
            self.connection.send(e)
            self.channel(str(e))

        def elems(e):
            self.device.device_root.elements.add_elem(e)

        self.reply = reply
        self.elems = elems
        while True:
            if self.connection is None:
                try:
                    self.connection, self.addr = self.socket.accept()
                except OSError:
                    self.channel("Socket was killed.")
                    break  # Socket was killed.
                continue
            data_from_socket = self.connection.recv(1024)
            if len(data_from_socket) != 0:
                self.channel("Received: %s" % str(data_from_socket))
            self.pipe.write(data_from_socket, reply=reply, elements=elems)
        if self.connection is not None:
            self.connection.close()

    def shutdown(self,  channel):
        self.channel("Shutting down server.")
        self.socket.close()

    def set_pipe(self, pipe):
        self.pipe = pipe
