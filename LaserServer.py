import socket

from Kernel import *


class LaserServer(Module):
    """
    Laser Server opens up a localhost server and waits, sends whatever data received to the pipe
    """
    def __init__(self, tcp=True, port=23, pipe=None, name='', greet=None):  # port 1040
        Module.__init__(self)
        self.tcp = tcp
        self.pipe = pipe
        self.port = port
        self.name = name
        self.greet = greet

        self.server_channel = None
        self.socket = None
        self.connection = None
        self.addr = None

    def initialize(self):
        if self.tcp:
            self.socket = socket.socket()
            self.socket.settimeout(2)
            self.socket.bind(('', self.port))
            self.socket.listen(5)
            self.device.threaded(self.tcp_run)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(2)
            self.socket.bind(('', self.port))
            self.device.threaded(self.udp_run)
        self.server_channel = self.device.channel_open('server')

    def udp_run(self):
        def reply(e):
            self.socket.sendto(e, address)
            # self.server_channel(str(e))

        def elems(e):
            self.device.device_root.elements.add_elem(e)

        try:
            if self.server_channel is not None:
                self.server_channel("UDP Socket Listening.")
            while True:
                try:
                    message, address = self.socket.recvfrom(1024)
                except socket.timeout:
                    if self.device.state == STATE_TERMINATE:
                        return
                    continue
                self.pipe.checksum_parse(message, reply=reply, elements=elems)
        except OSError:
            pass

    def tcp_run(self):
        """
        TCP Run is a connection thread delegate. Any connections are given a different threaded
        handle to interact with that connection. This thread here waits for sockets and delegates.
        """
        while True:
            connection = None
            addr = None
            try:
                connection, addr = self.socket.accept()
                self.server_channel("Socket Connected: %s" % str(addr))
                self.device.threaded(self.tcp_connection_handle(connection, addr))
            except socket.timeout:
                if self.device.state == STATE_TERMINATE:
                    return
                continue
            except OSError:
                self.server_channel("Socket was killed: %s" % str(addr))
                if connection is not None:
                    connection.close()
                if self.device.state == STATE_TERMINATE:
                    return

    def tcp_connection_handle(self, connection, addr):
        """
        The TCP Connection Handle, handles all connections delegated by the tcp_run() method.
        The threaded context is entirely local and independent.
        """
        def reply(e):
            if connection is not None:
                connection.send(bytes(e, 'utf-8'))
                self.server_channel("<-- %s" % str(e))

        def elems(e):
            self.device.device_root.elements.add_elem(e)

        def handle():
            if self.greet is not None:
                reply(self.greet)
            while True:
                try:
                    data_from_socket = connection.recv(1024)
                    if len(data_from_socket) != 0:
                        self.server_channel("--> %s" % str(data_from_socket))
                    self.pipe.write(data_from_socket, reply=reply, elements=elems)
                except socket.error:
                    if connection is not None:
                        connection.close()
                    break
        return handle

    def shutdown(self,  channel):
        self.server_channel("Shutting down server.")
        self.socket.close()

    def set_pipe(self, pipe):
        self.pipe = pipe
