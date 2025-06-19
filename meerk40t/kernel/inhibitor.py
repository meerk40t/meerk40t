"""
This modules prevents the OS from sleeping / hibernating.
It is used to ensure that the system remains active during long-running operations.
It is not intended to be used for general-purpose tasks.
"""

import ctypes
import platform
import subprocess

_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001

# map each OS to a pair of (inhibit_fn, release_fn)
_ACTIONS = {
    "Darwin": {
        "inhibit": lambda: subprocess.call(["caffeinate", "-i"]),
        "release": lambda: subprocess.call(["killall", "caffeinate"]),
    },
    "Linux": {
        "inhibit": lambda: subprocess.run(
            [
                "systemctl",
                "mask",
                "sleep.target",
                "suspend.target",
                "hibernate.target",
                "hybrid-sleep.target",
            ]
        ),
        "release": lambda: subprocess.run(
            [
                "systemctl",
                "unmask",
                "sleep.target",
                "suspend.target",
                "hibernate.target",
                "hybrid-sleep.target",
            ]
        ),
    },
    "Windows": {
        "inhibit": lambda: ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED
        ),
        "release": lambda: ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS
        ),
    },
}


class Inhibitor:
    def __init__(self):
        self._os = platform.system()
        self.active = False
        self._actions = _ACTIONS.get(self._os)

    @property
    def available(self) -> bool:
        return self._actions is not None

    def inhibit(self):
        if not self.available or self.active:
            return
        self._actions["inhibit"]()
        self.active = True

    def release(self):
        if not self.available or not self.active:
            return
        self._actions["release"]()
        self.active = False

    @property
    def status(self) -> str:
        if not self.available:
            return f"Inhibitor not implemented for {self._os}"
        return "Inhibitor is active" if self.active else "Inhibitor is not active"
