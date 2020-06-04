import socket
import threading

from Kernel import *


class ServerThread(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self, name='ServerThread')
        self.server = server
        self.state = None
        self.connection = None
        self.addr = None
        self.set_state(STATE_INITIALIZE)
        self.buffer = None

    def set_state(self, state):
        if self.state != state:
            self.state = state

    def udp_run(self):
        try:
            reply = lambda e: self.server.socket.sendto(e, address)
            elements = lambda e: self.server.device.device_root.elements.add_elem(e)
            while True:
                message, address = self.server.socket.recvfrom(1024)
                self.server.pipe.checksum_parse(message, reply=reply, elements=elements)
        except OSError:
            pass

    def tcp_run(self):
        while self.state != STATE_TERMINATE and self.state != STATE_END:
            if self.connection is None:
                try:
                    self.connection, self.addr = self.server.socket.accept()
                except OSError:
                    self.server.channel("Socket was killed.")
                    break  # Socket was killed.
                continue
            if self.state == STATE_PAUSE:
                while self.state == STATE_PAUSE:
                    time.sleep(1)
                    if self.state == STATE_TERMINATE:
                        return
                self.set_state(STATE_ACTIVE)

            push_message = self.server.pipe.read(1024)
            if push_message is not None:
                if isinstance(push_message, str):
                    push_message = push_message.encode('utf8')
                if len(push_message) != 0:
                    print(push_message)
                self.connection.send(push_message)

            data_from_socket = self.connection.recv(1024)
            if len(data_from_socket) != 0:
                self.server.channel("Received: %s" % str(data_from_socket))
            self.server.pipe.write(data_from_socket)

            push_message = self.server.pipe.read(1024)
            if push_message is not None:
                if isinstance(push_message, str):
                    push_message = push_message.encode('utf8')
                if len(push_message) != 0:
                    print(push_message)
                self.connection.send(push_message)
        if self.connection is not None:
            self.connection.close()

    def run(self):
        self.set_state(STATE_ACTIVE)
        if self.server.tcp:
            self.tcp_run()
        else:
            self.udp_run()


class LaserServer(Module):
    """
    Laser Server opens up a localhost server and waits, sends whatever data received to the pipe
    """
    def __init__(self, tcp=True, port=1040, pipe=None, name=''):
        Module.__init__(self)
        self.tcp = tcp
        self.pipe = pipe
        self.port = port
        self.name = name

        self.socket = None
        self.thread = None
        self.channel = lambda e: e

    def initialize(self):
        if self.tcp:
            self.socket = socket.socket()
            self.socket.bind(('', self.port))
            self.socket.listen(1)
        else:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('', self.port))
        self.thread = ServerThread(self)
        self.device.control_instance_add('Set_Server_Pipe' + self.name, self.set_pipe)
        self.device.thread_instance_add('ServerThread', self.thread)
        self.thread.start()
        self.channel = self.device.channel_open('server')

    def shutdown(self,  channel):
        self.channel("Shutting down server.")
        self.socket.close()
        self.thread.state = STATE_END

    def set_pipe(self, pipe):
        self.pipe = pipe
