"""Standalone kernel enabling sophisticated console / UI applications."""
import gettext

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


def _(message):
    return _gettext(message)


def set_language(domain, localedir, language):
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

    for localedir in localedirs:
        el = gettext.translation(
            domain, localedir=localedir, languages=[language]
        )
        el.install()
        global _gettext
        _gettext = el.gettext
