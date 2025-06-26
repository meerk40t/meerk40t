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

# Extract common target list up top
_SYSTEMCTL_TARGETS = [
    "sleep.target",
    "suspend.target",
    "hibernate.target",
    "hybrid-sleep.target",
]


def _run_systemctl(action: str):
    try:
        # Check if systemctl is available
        proc = subprocess.run(["systemctl", action] + _SYSTEMCTL_TARGETS)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("systemctl is not available on this system.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
    # print(f"systemctl {action} returned {proc.returncode} [{proc}]")
    return proc.returncode == 0


def _darwin_inhibit():
    try:
        proc = subprocess.run(["caffeinate", "-i"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("caffeinate is not available on this system.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
    return proc.returncode == 0


def _darwin_release():
    try:
        # Use killall to stop caffeinate
        proc = subprocess.run(["killall", "caffeinate"])
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
    return proc.returncode == 0


def _linux_inhibit():
    return _run_systemctl("mask")


def _linux_release():
    return _run_systemctl("unmask")


def _windows_inhibit():
    try:
        # Set the thread execution state to prevent sleep
        ctypes.windll.kernel32.SetThreadExecutionState(
            _ES_CONTINUOUS | _ES_SYSTEM_REQUIRED
        )
    except Exception as e:
        print(f"An error occurred while setting thread execution state: {e}")
        return False
    return True


def _windows_release():
    try:
        # Reset the thread execution state to allow sleep
        ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
    except Exception as e:
        print(f"An error occurred while resetting thread execution state: {e}")
        return False
    return True


# Darwin does not have a systemctl, but uses caffeinate
# Linux uses systemctl to mask/unmask sleep targets
# Windows uses SetThreadExecutionState to prevent sleep
# NB: Darwin does not to work relaibly on my testsystem, so has been disabled
_ACTIONS = {
    # "Darwin": {"inhibit": _darwin_inhibit, "release": _darwin_release},
    "Linux": {"inhibit": _linux_inhibit, "release": _linux_release},
    "Windows": {"inhibit": _windows_inhibit, "release": _windows_release},
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
        if self._actions["inhibit"]():
            self.active = True

    def release(self):
        if not self.available or not self.active:
            return
        if self._actions["release"]():
            self.active = False
