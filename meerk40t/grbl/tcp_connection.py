"""
TCP Connection

Communicate with a TCP network destination with the GRBL driver.
"""

import socket
import threading
import time


class TCPOutput:
    def __init__(self, context, name=None):
        super().__init__()
        self.service = context
        self._stream = None
        self._read_buffer_size = 1024
        self.read_buffer = bytearray()
        self.name = name

        self._write_lock = threading.Condition()
        self.buffer = bytearray()
        self.thread = None

    @property
    def connected(self):
        return self._stream is not None

    def connect(self):
        try:
            self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._stream.connect((self.service.address, self.service.port))
            self.service.signal("tcp;status", "connected")
        except TimeoutError:
            self.disconnect()
            self.service.signal("tcp;status", "timeout connect")
        except ConnectionError:
            self.disconnect()
            self.service.signal("tcp;status", "connection error")
        except socket.gaierror as e:
            self.disconnect()
            self.service.signal("tcp;status", "address resolve error")
        except socket.herror as e:
            self.disconnect()
            self.service.signal("tcp;status", f"herror: {str(e)}")
        except OSError as e:
            self.disconnect()
            self.service.signal("tcp;status", f"Host down {str(e)}")

    def disconnect(self):
        self.service.signal("tcp;status", "disconnected")
        self._stream.close()
        self._stream = None

    def write(self, data):
        self.service.signal("tcp;write", data)
        if isinstance(data, str):
            data = bytes(data, "utf-8")
        with self._write_lock:
            self.buffer += data
            self.service.signal("tcp;buffer", len(self.buffer))
            self._write_lock.notify()
        self._start()

    realtime_write = write

    def read(self):
        self.read_buffer += self._stream.recv(self._read_buffer_size)
        f = self.read_buffer.find(b"\n")
        if f == -1:
            return None
        response = self.read_buffer[:f]
        self.read_buffer = self.read_buffer[f + 1 :]
        str_response = str(response, "raw_unicode_escape")
        str_response = str_response.strip()
        return str_response

    @property
    def viewbuffer(self):
        return self.buffer.decode("utf8")

    def _start(self):
        if self.thread is None:
            self.thread = self.service.threaded(
                self._sending,
                thread_name=f"sender-{self.service.port}",
                result=self._stop,
            )

    def _stop(self, *args):
        self.thread = None

    def _sending(self):
        while True:
            if not self.buffer:
                with self._write_lock:
                    if not self.buffer:
                        self._write_lock.wait()
            try:
                if self._stream is None:
                    self.connect()
                    if self._stream is None:
                        raise ConnectionError

                with self._write_lock:
                    sent = self._stream.send(self.buffer)
                    del self.buffer[:sent]
                    self.service.signal("tcp;buffer", len(self.buffer))
            except (ConnectionError, OSError):
                self.disconnect()
                time.sleep(0.05)

    def __repr__(self):
        if self.name is not None:
            return (
                f"TCPOutput('{self.service.location()}','{self.name}')"
            )
        return f"TCPOutput('{self.service.location()}')"

    def __len__(self):
        return len(self.buffer)
