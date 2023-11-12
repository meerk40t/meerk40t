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
    el = gettext.translation(domain, localedir=localedir, languages=[language], fallback=True)
    el.install()
    global _gettext
    _gettext = el.gettext
