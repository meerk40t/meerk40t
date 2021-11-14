import socket
import threading
import time


def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        kernel.register("output/file", FileOutput)
        kernel.register("output/tcp", TCPOutput)


class FileOutput:
    def __init__(self, filename, name=None):
        super().__init__()
        self.next = None
        self.prev = None
        self.filename = filename
        self._stream = None
        self.name = name

    def writable(self):
        return True

    def write(self, data):
        filename = self.filename.replace("?", "").replace(":", "")
        with open(
            filename, "ab" if isinstance(data, (bytes, bytearray)) else "a"
        ) as stream:
            stream.write(data)
            stream.flush()

    def __repr__(self):
        if self.name is not None:
            return "FileOutput('%s','%s')" % (self.filename, self.name)
        return "FileOutput(%s)" % self.filename

    def __len__(self):
        return 0

    realtime_write = write

    @property
    def type(self):
        return "file"


class TCPOutput:
    def __init__(self, context, address, port, name=None):
        super().__init__()
        self.context = context
        self.next = None
        self.prev = None
        self.address = address
        self.port = port
        self._stream = None
        self.name = name

        self.lock = threading.RLock()
        self.buffer = bytearray()
        self.thread = None

    def writable(self):
        return True

    def connect(self):
        try:
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._stream.connect((self.address, self.port))
            self.context.signal("tcp;status", "connected")
        except (ConnectionError, TimeoutError):
            self.disconnect()

    def disconnect(self):
        self.context.signal("tcp;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.context.signal("tcp;write", data)
        with self.lock:
            self.buffer += data
            self.context.signal("tcp;buffer", len(self.buffer))
        self._start()

    realtime_write = write

    def _start(self):
        if self.thread is None:
            self.thread = self.context.threaded(
                self._sending, thread_name="sender-%d" % self.port, result=self._stop
            )

    def _stop(self, *args):
        self.thread = None

    def _sending(self):
        tries = 0
        while True:
            try:
                if len(self.buffer):
                    if self._stream is None:
                        self.connect()
                        if self._stream is None:
                            return
                    with self.lock:
                        sent = self._stream.send(self.buffer)
                        del self.buffer[:sent]
                        self.context.signal("tcp;buffer", len(self.buffer))
                    tries = 0
                else:
                    tries += 1
                    time.sleep(0.1)
            except (ConnectionError, OSError):
                tries += 1
                self.disconnect()
                time.sleep(0.05)
            if tries >= 20:
                with self.lock:
                    if len(self.buffer) == 0:
                        break

    def __repr__(self):
        if self.name is not None:
            return "TCPOutput('%s:%s','%s')" % (self.address, self.port, self.name)
        return "TCPOutput('%s:%s')" % (self.address, self.port)

    def __len__(self):
        return len(self.buffer)

    @property
    def type(self):
        return "tcp"

