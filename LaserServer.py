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
        self.set_state(THREAD_STATE_UNSTARTED)
        self.buffer = None

    def set_state(self, state):
        if self.state != state:
            self.state = state

    def run(self):
        self.set_state(THREAD_STATE_STARTED)

        while self.state != THREAD_STATE_ABORT and self.state != THREAD_STATE_FINISHED:
            if self.connection is None:
                try:
                    self.connection, self.addr = self.server.socket.accept()
                except OSError:
                    break  # Socket was killed.
                continue
            if self.state == THREAD_STATE_PAUSED:
                while self.state == THREAD_STATE_PAUSED:
                    time.sleep(1)
                    if self.state == THREAD_STATE_ABORT:
                        return
                self.set_state(THREAD_STATE_STARTED)

            push_message = self.server.pipe.read(1024)
            if push_message is not None:
                if isinstance(push_message, str):
                    push_message = push_message.encode('utf8')
                    print(push_message)
                self.connection.send(push_message)

            data_from_socket = self.connection.recv(1024)
            self.server.pipe.write(data_from_socket)
            print(data_from_socket)

            push_message = self.server.pipe.read(1024)
            if push_message is not None:
                if isinstance(push_message, str):
                    push_message = push_message.encode('utf8')
                    print(push_message)
                self.connection.send(push_message)
        if self.connection is not None:
            self.connection.close()


class LaserServer(Module):
    """
    Laser Server opens up a localhost server and waits, sends whatever data received to the pipe
    """
    def __init__(self, port=1040, pipe=None, name=''):
        Module.__init__(self)
        self.pipe = pipe
        self.port = port
        self.name = name

        self.socket = None
        self.thread = None
        self.kernel = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        self.name = name
        self.socket = socket.socket()
        self.socket.bind(('', self.port))
        self.socket.listen(1)
        self.thread = ServerThread(self)
        self.kernel.add_control('Set_Server_Pipe' + self.name, self.set_pipe)
        self.kernel.add_thread('ServerThread', self.thread)
        self.thread.start()

    def shutdown(self, kernel):
        Module.shutdown(self, kernel)
        self.socket.close()
        self.thread.state = THREAD_STATE_FINISHED

    def set_pipe(self, pipe):
        self.pipe = pipe
