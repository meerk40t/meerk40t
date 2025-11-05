"""
TCP Connection handles Ruida TCP data sending and receiving and the Ruida Bridge Protocol.

"""

import queue
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
        self.swizzle = None
        self.unswizzle = None
        
        # Receive buffer for synchronous protocol handler compatibility
        self._recv_buffer = queue.Queue()
        self._recv_lock = threading.Lock()

    def set_swizzles(self, swizzle, unswizzle):
        """Set swizzle functions for use by the controller."""
        self.swizzle = swizzle
        self.unswizzle = unswizzle

    def open(self):
        if self.connected:
            return
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Enable TCP keep-alive to prevent connection timeouts
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Set keep-alive parameters (platform-dependent)
            try:
                self.socket.setsockopt(socket.IPPROTO_TCP, getattr(socket, "TCP_KEEPIDLE", 60), 60)
                self.socket.setsockopt(socket.IPPROTO_TCP, getattr(socket, "TCP_KEEPINTVL", 30), 30)
                self.socket.setsockopt(socket.IPPROTO_TCP, getattr(socket, "TCP_KEEPCNT", 3), 3)
            except (AttributeError, OSError):
                pass  # Not all platforms support these options
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
        except Exception as e:
            self.close()
            self.service.signal("tcp;status", f"unknown error on connect: {str(e)}")

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
                
                # Put data in buffer for synchronous protocol handler
                self._recv_buffer.put(message)
                
                # Also send to channel for backward compatibility
                self.recv_channel(message)
        except OSError:
            pass

    def send(self, data):
        """Send data directly via TCP."""
        self.write(data)

    def recv(self):
        """Receive data - supports both synchronous protocol handler and async channels."""
        try:
            # Try to get data from buffer with timeout for protocol handler compatibility
            return self._recv_buffer.get(timeout=0.1)
        except queue.Empty:
            return None  # No data available
