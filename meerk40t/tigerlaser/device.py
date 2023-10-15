"""

"""
from meerk40t.core.view import View

from meerk40t.kernel import Service

from ..core.spoolers import Spooler
from ..core.units import Length
from .driver import TigerDriver


class TigerDevice(Service):
    """
    Tiger Device Service.
    """

    def __init__(self, kernel, path, *args, choices=None, **kwargs):
        Service.__init__(self, kernel, path)

        _ = self._
        choices = [
            {
                "attr": "label",
                "object": self,
                "default": "tiger",
                "type": str,
                "label": _("Label"),
                "tip": _("What is this device called."),
                "section": "_00_General",
                "signals": "device;renamed",
            },
            {
                "attr": "bedwidth",
                "object": self,
                "default": "25mm",
                "type": Length,
                "label": _("Width"),
                "tip": _("Width of the laser bed."),
                "section": "_10_Dimensions",
                "subsection": "Bed",
                "signals": "bedsize",
                "nonzero": True,
            },
            {
                "attr": "bedheight",
                "object": self,
                "default": "25mm",
                "type": Length,
                "label": _("Height"),
                "tip": _("Height of the laser bed."),
                "section": "_10_Dimensions",
                "subsection": "Bed",
                "signals": "bedsize",
                "nonzero": True,
            },
        ]
        self.register_choices("bed_dim", choices)

        self.view = View(self.bedwidth, self.bedheight, dpi=1000.0)

        self.state = 0

        self.driver = TigerDriver(self)
        self.add_service_delegate(self.driver)

        self.spooler = Spooler(self, driver=self.driver)
        self.add_service_delegate(self.spooler)

    @property
    def viewbuffer(self):
        return "No buffer."

    @property
    def current(self):
        """
        @return: the location in units for the current known position.
        """
        return self.view.iposition(self.driver.native_x, self.driver.native_y)

    @property
    def native(self):
        """
        @return: the location in device native units for the current known position.
        """
        return self.driver.native_x, self.driver.native_y
