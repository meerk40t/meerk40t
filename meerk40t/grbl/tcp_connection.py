"""
TCP Connection

Communicate with a TCP network destination with the GRBL driver.
"""

import socket
import time


def probe_grbl_port(address, ports, timeout=2.5):
    """
    Return the first TCP port that answers like GRBL (MKS DLC32 often uses 8080, not 23).
    """
    seen = set()
    for port in ports:
        if port in seen or port < 1 or port > 65535:
            continue
        seen.add(port)
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((address, port))
            sock.sendall(b"\r\n")
            chunk = sock.recv(128)
            if chunk:
                return port
        except OSError:
            pass
        finally:
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
    return None


def resolve_grbl_tcp_port(address, preferred_port):
    """Prefer configured port, then MKS DLC32 defaults (8080), then classic telnet (23)."""
    candidates = []
    for port in (preferred_port, 8080, 23):
        if port not in candidates:
            candidates.append(port)
    return probe_grbl_port(address, candidates)


def wake_lan_host(address, http_port=80, attempts=6, delay=0.5):
    """
    MKS DLC32 / Grbl_Esp32 may not answer TCP until something hits the web UI first.
    Mimics opening http://<address>/ on a phone before MeerK40t connects on port 23.
    """
    for attempt in range(attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((address, http_port))
            sock.sendall(
                f"GET / HTTP/1.0\r\nHost: {address}\r\nConnection: close\r\n\r\n".encode(
                    "ascii"
                )
            )
            try:
                sock.recv(512)
            except OSError:
                pass
            sock.close()
            return True
        except OSError:
            try:
                sock.close()
            except Exception:
                pass
            if attempt + 1 < attempts:
                time.sleep(delay)
    return False


class TCPOutput:
    def __init__(self, service, controller, name=None):
        self.service = service
        self.controller = controller
        self._stream = None
        self._read_buffer_size = 1024
        self.read_buffer = bytearray()
        self.name = name

    @property
    def connected(self):
        return self._stream is not None

    def connect(self):
        try:
            self.controller.log("Attempting to Connect...", type="connection")
            address = self.service.address
            configured_port = min(65535, max(0, self.service.port))
            if not wake_lan_host(address):
                self.controller.log(
                    "Wake HTTP failed; trying GRBL port anyway...",
                    type="connection",
                )
            port = resolve_grbl_tcp_port(address, configured_port)
            if port is None:
                port = configured_port
            elif port != configured_port:
                self.controller.log(
                    f"GRBL on port {port} (device was set to {configured_port}); "
                    f"update Configuration → Interface → port to {port}.",
                    type="connection",
                )
            last_error = None
            for attempt in range(4):
                try:
                    if self._stream is not None:
                        self._stream.close()
                    self._stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self._stream.settimeout(8.0)
                    # Enable TCP keep-alive to prevent connection timeouts
                    self._stream.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    try:
                        self._stream.setsockopt(
                            socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60
                        )
                        self._stream.setsockopt(
                            socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30
                        )
                        self._stream.setsockopt(
                            socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3
                        )
                    except (AttributeError, OSError):
                        pass
                    if attempt > 0:
                        found = resolve_grbl_tcp_port(address, port)
                        if found is not None:
                            port = found
                    self._stream.connect((address, port))
                    # Blocking reads: $$ validation over Wi-Fi can take >8s between chunks
                    self._stream.settimeout(None)
                    last_error = None
                    break
                except OSError as e:
                    last_error = e
                    if attempt + 1 < 4:
                        wake_lan_host(address, attempts=2, delay=0.3)
                        time.sleep(0.8)
            if last_error is not None:
                raise last_error
            self.service.signal("grbl;status", "connected")
        except TimeoutError:
            self.disconnect()
            self.service.signal("grbl;status", "timeout connect")
        except ConnectionError:
            self.disconnect()
            self.service.signal("grbl;status", "connection error")
        except (socket.gaierror, OverflowError) as e:
            self.disconnect()
            self.service.signal("grbl;status", f"address resolve error: {str(e)}")
        except socket.herror as e:
            self.disconnect()
            self.service.signal("grbl;status", f"herror: {str(e)}")
        except OSError as e:
            self.disconnect()
            self.service.signal("grbl;status", f"Host down {str(e)}")
        except Exception as e:
            self.disconnect()
            self.service.signal("grbl;status", f"unknown error on connect: {str(e)}")

    def disconnect(self):
        self.controller.log("Disconnected", type="connection")
        self.service.signal("grbl;status", "disconnected")
        if self._stream is not None:
            self._stream.close()
        self._stream = None

    def write(self, data):
        self.service.signal("grbl;write", data)
        if isinstance(data, str):
            data = bytes(data, "utf-8")
        while data:
            try:
                sent = self._stream.send(data)
            except Exception as e:
                self.disconnect()
                self.service.signal("grbl;status", f"unknown error on write: {str(e)}")
                return
            if sent == len(data):
                return
            data = data[sent:]

    realtime_write = write

    def read(self):
        f = self.read_buffer.find(b"\n")
        if f == -1:
            try:
                chunk = self._stream.recv(self._read_buffer_size)
                if not chunk:
                    self.disconnect()
                    self.service.signal("grbl;status", "connection closed by device")
                    return
                self.read_buffer += chunk
            except (TimeoutError, socket.timeout):
                return
            except OSError as e:
                self.disconnect()
                self.service.signal("grbl;status", f"unknown error on read: {str(e)}")
                return
            except Exception as e:
                self.disconnect()
                self.service.signal("grbl;status", f"unknown error on read: {str(e)}")
                return
            f = self.read_buffer.find(b"\n")
            if f == -1:
                return
        response = self.read_buffer[:f]
        self.read_buffer = self.read_buffer[f + 1 :]
        str_response = str(response, "latin-1")
        str_response = str_response.strip()
        return str_response

    def __repr__(self):
        if self.name is not None:
            return f"TCPOutput('{self.service.location()}','{self.name}')"
        return f"TCPOutput('{self.service.location()}')"
