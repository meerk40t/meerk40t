import wx

from meerk40t.gui.toolwidgets.toolwidget import ToolWidget

from ...core.units import UNITS_PER_MM
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME


class RelocateTool(ToolWidget):
    """
    Relocate laser Tool.

    Adds Circle with click and drag.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.p1 = None
        self.p2 = None

    def process_draw(self, gc: wx.GraphicsContext):
        pass

    def event(self, window_pos=None, space_pos=None, event_type=None):
        # We dont use tool_active here, or should we?
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            bed_width = self.scene.context.device.unit_width
            bed_height = self.scene.context.device.unit_height
            x = space_pos[0]
            y = space_pos[1]
            if x > bed_width:
                x = bed_width
            if y > bed_height:
                y = bed_height
            if x < 0:
                x = 0
            if y < 0:
                y = 0
            x /= UNITS_PER_MM
            y /= UNITS_PER_MM
            self.scene.context("move_absolute {x}mm {y}mm\n".format(x=x, y=y))
            response = RESPONSE_CONSUME
        return response