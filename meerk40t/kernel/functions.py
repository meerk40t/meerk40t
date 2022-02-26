import os
import os.path
import platform
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple, Union

def get_safe_path(
    name: str, create: Optional[bool] = False, system: Optional[str] = None
) -> str:
    """
    Get a path which should have valid user permissions in an OS dependent method.

    @param name: directory name within the safe OS dependent userdirectory
    @param create: Should this directory be created if needed.
    @param system: Override the system value determination
    @return:
    """
    if not system:
        system = platform.system()

    if system == "Darwin":
        directory = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            name,
        )
    elif system == "Windows":
        directory = os.path.join(os.path.expandvars("%LOCALAPPDATA%"), name)
    else:
        directory = os.path.join(os.path.expanduser("~"), ".config", name)
    if directory is not None and create:
        os.makedirs(directory, exist_ok=True)
    return directory
