"""
TCP Connection handles Ruida TCP data sending and receiving and the Ruida Bridge Protocol.

"""

import socket
import struct
import threading
import time


class TCPConnection:
    def __init__(self, service):
        self.service = service
        name = self.service.label.replace(" ", "-")
        name = name.replace("/", "-")

        self.recv_channel = service.channel(f"{name}/recv", pure=True)
        self.send_channel = service.channel(f"{name}/send", pure=True)
        self.events = service.channel(f"{name}/events", pure=True)

        self.is_shutdown = False
        self.socket = None
        self._send_lock = threading.Condition()
        self.buffer = bytearray()
        self.thread = None

    @property
    def port(self):
        return self.service.tcp_port

    def address(self):
        return self.service.tcp_address

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    def open(self):
        if self.connected:
            return
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Make sure port is in a valid range...
            port = min(65535, max(0, self.service.port))
            self.socket.connect((self.service.address, port))
            self.service.signal("tcp;status", "connected")
            name = self.service.label.replace(" ", "-")
            name = name.replace("/", "-")
            self.service.threaded(
                self._run_tcp_send, thread_name=f"tcpsend-{name}", daemon=True
            )
            self.service.threaded(
                self.run_tcp_recv, thread_name=f"tcprecv-{name}", daemon=True
            )
            self.service.signal("pipe;usb_status", "connected")
            self.events("Connected")
        except TimeoutError:
            self.close()
            self.service.signal("tcp;status", "timeout connect")
        except ConnectionError:
            self.close()
            self.service.signal("tcp;status", "connection error")
        except (socket.gaierror, OverflowError) as e:
            self.close()
            self.service.signal("tcp;status", "address resolve error")
        except socket.herror as e:
            self.close()
            self.service.signal("tcp;status", f"herror: {str(e)}")
        except OSError as e:
            self.close()
            self.service.signal("tcp;status", f"Host down {str(e)}")

    def close(self):
        if not self.connected:
            return
        self.socket.close()
        self.socket = None
        self.service.signal("pipe;usb_status", "disconnected")
        self.events("Disconnected")

    @property
    def is_connecting(self):
        return False

    @property
    def connected(self):
        return not self.is_shutdown and self.socket is not None

    def abort_connect(self):
        pass

    def write(self, data):
        """
        Process not only the checksum for UDP but the `L<length>` preamble for the TCP.
        @param data:
        @return:
        """
        self.open()
        data = (
            b"L"
            + struct.pack(">H", len(data) & 0xFFFF)
            + struct.pack(">H", sum(data) & 0xFFFF)
            + data
        )
        with self._send_lock:
            self.buffer += data
            self._send_lock.notify()

    def _run_tcp_send(self):
        tries = 0
        while self.connected:
            try:
                if not self.buffer:
                    if self.socket is None:
                        self.open()
                        if self.socket is None:
                            return
                    with self._send_lock:
                        sent = self.socket.send(self.buffer)
                        packet = self.buffer[:sent]
                        del self.buffer[:sent]
                        self.service.signal("tcp;buffer", len(self.buffer))
                        self.send_channel(packet)
                    tries = 0
                else:
                    tries += 1
                    time.sleep(0.1)
            except (ConnectionError, OSError):
                tries += 1
                self.close()
                time.sleep(0.05)
            if tries >= 20:
                with self._send_lock:
                    if len(self.buffer) == 0:
                        break

    def run_tcp_recv(self):
        try:
            while self.connected:
                try:
                    message, address = self.socket.recv(1024)
                except (socket.timeout, AttributeError):
                    continue
                self.recv_channel(message)
        except OSError:
            pass
