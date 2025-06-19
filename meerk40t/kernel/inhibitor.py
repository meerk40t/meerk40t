"""
This modules prevents the OS from sleeping / hibernating.
It is used to ensure that the system remains active during long-running operations.
It is not intended to be used for general-purpose tasks.
"""

from platform import system


class InhibitorWindows:
    """Inhibitor class for Windows."""

    """https://msdn.microsoft.com/en-us/library/windows/desktop/aa373208(v=vs.85).aspx"""
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001

    def inhibit(self):
        import ctypes

        # print('Inhibit (prevent) suspend mode')
        ctypes.windll.kernel32.SetThreadExecutionState(
            self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED
        )

    def release(self):
        import ctypes

        # print('Release (allow) suspend mode')
        ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)


class InhibitorLinux:
    """Inhibitor class for Linux."""

    def inhibit(self):
        """Inhibit the OS from sleeping."""
        import ctypes

        self._handle = ctypes.CDLL("libc.so.6").system(
            "dbus-send --print-reply --dest=org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager.Inhibit string:'sleep' string:'meerk40t'"
        )

    def release(self):
        """Release the inhibition."""
        import ctypes

        self._handle = ctypes.CDLL("libc.so.6").system(
            "dbus-send --print-reply --dest=org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager.UnInhibit string:'meerk40t'"
        )


class Inhibitor:
    """Inhibitor class to prevent the OS from sleeping."""

    def __init__(self):
        self.available = True
        self._inhibit = None
        self.active: bool = False
        self.available = system() in ("Linux", "Windows")

    def inhibit(self):
        """Inhibit the OS from sleeping."""
        if not self.available:
            return
        if system() == "Linux":
            self._inhibit = InhibitorLinux()
        elif system() == "Windows":
            self._inhibit = InhibitorWindows()
        self._inhibit.inhibit()
        self.active = True

    def release(self):
        """Release the inhibition."""
        if not self.available:
            return
        if self._inhibit:
            self._inhibit.release()
            self._inhibit = None
            self.active = False

    @property
    def status(self):
        """Check if the inhibitor is active."""
        if self.available:
            return "Inhibitor is active" if self.active else "Inhibitor is not active"
        else:
            return "Inhibitor not implemented for this OS"
