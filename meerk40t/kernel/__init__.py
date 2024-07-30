"""Standalone kernel enabling sophisticated console / UI applications."""

from .channel import *
from .context import *
from .exceptions import *
from .functions import *
from .jobs import *
from .kernel import *
from .lifecycles import *
from .module import *
from .service import *
from .settings import *

_gettext = lambda e: e
_gettext_language = None


def _(message):
    return _gettext(message)


def set_language(domain, localedir, language):
    import gettext
    import sys

    localedirs = list()
    try:  # pyinstaller internal location
        # pylint: disable=no-member
        _resource_path = os.path.join(sys._MEIPASS, localedir)
        localedirs.append(_resource_path)
    except Exception:
        pass

    try:  # Mac py2app resource
        _resource_path = os.path.join(os.environ["RESOURCEPATH"], localedir)
        localedirs.append(_resource_path)
    except Exception:
        pass

    localedirs.append(localedir)

    # Default Locale, prepended. Check this first.
    basepath = os.path.abspath(os.path.dirname(sys.argv[0]))
    working_dir = os.path.join(basepath, localedir)
    localedirs.append(working_dir)

    localedirs.append(None)

    for ld in localedirs:
        try:
            el = gettext.translation(
                domain,
                localedir=ld,
                languages=[language],
                fallback=ld is None,
            )
        except (FileNotFoundError, PermissionError, OSError):
            continue
        el.install()
        global _gettext, _gettext_language
        _gettext = el.gettext
        _gettext_language = language
        break
