import socket

from Kernel import *


class LaserServer(Module):
    """
    Laser Server opens up a localhost server and waits, sends whatever data received to the pipe
    """
    def __init__(self, context, path, tcp=True, port=23, pipe=None, name='', greet=None):  # port 1040
        Module.__init__(self, context, path)
        self.context_root = context.get_context('/')
        self.tcp = tcp
        self.pipe = pipe
        self.port = port
        self.name = name
        self.greet = greet

        self.server_channel = None
        self.socket = None
        self.connection = None
        self.addr = None

    def initialize(self, channel=None):
        if self.tcp:
            self.context.threaded(self.tcp_run)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(2)
            self.socket.bind(('', self.port))
            self.context.threaded(self.udp_run)
        self.server_channel = self.context.channel_open('server')

    def finalize(self, channel=None):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def shutdown(self,  channel=None):
        self.server_channel("Shutting down server.")
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def udp_run(self):
        def reply(e):
            self.socket.sendto(e, address)

        def elems(e):
            self.context_root.elements.add_elem(e)

        try:
            if self.server_channel is not None:
                self.server_channel("UDP Socket Listening.")
            while True:
                try:
                    message, address = self.socket.recvfrom(1024)
                except socket.timeout:
                    if self.context.state == STATE_TERMINATE:
                        return
                    continue
                if self.port == 50207:
                    self.pipe.jog_parse(message, reply=reply, elements=elems)
                else:
                    self.pipe.checksum_parse(message, reply=reply, elements=elems)
        except OSError:
            pass

    def tcp_run(self):
        """
        TCP Run is a connection thread delegate. Any connections are given a different threaded
        handle to interact with that connection. This thread here waits for sockets and delegates.
        """
        self.socket = socket.socket()
        self.socket.settimeout(2)
        try:
            self.socket.bind(('', self.port))
            self.socket.listen(5)
        except OSError:
            self.server_channel("Could not start listening.")
            return

        while self.context.state != STATE_TERMINATE:
            self.server_channel("Listening %s on port %d..." % (self.name, self.port))
            connection = None
            addr = None
            try:
                connection, addr = self.socket.accept()
                self.server_channel("Socket Connected: %s" % str(addr))
                self.context.threaded(self.tcp_connection_handle(connection, addr))
            except socket.timeout:
                pass
            except OSError:
                self.server_channel("Socket was killed: %s" % str(addr))
                if connection is not None:
                    connection.close()
                break
        self.socket.close()

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
            self.context_root.elements.add_elem(e)

        def handle():
            if self.greet is not None:
                reply(self.greet)
            while self.context.state != STATE_TERMINATE:
                try:
                    data_from_socket = connection.recv(1024)
                    if len(data_from_socket) != 0:
                        self.server_channel("--> %s" % str(data_from_socket))
                    self.pipe.write(data_from_socket, reply=reply, elements=elems)
                except socket.timeout:
                    self.server_channel("Connection to %s timed out." % str(addr))
                    break
                except socket.error:
                    if connection is not None:
                        connection.close()
                    break
        return handle

    def set_pipe(self, pipe):
        self.pipe = pipe
