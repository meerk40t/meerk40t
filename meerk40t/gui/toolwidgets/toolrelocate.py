import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget

from ...core.units import UNITS_PER_MM


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

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        # Add snap behaviour
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.scene.pane.tool_active = True
            response = RESPONSE_CONSUME
        elif event_type == "move":
            if self.scene.pane.tool_active:
                response = RESPONSE_CONSUME
        elif event_type in ("leftup", "leftclick"):
            bed_width = self.scene.context.device.unit_width
            bed_height = self.scene.context.device.unit_height
            if nearest_snap is None:
                x = space_pos[0]
                y = space_pos[1]
            else:
                x = nearest_snap[0]
                y = nearest_snap[1]

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
            self.scene.context(f"move_absolute {x}mm {y}mm\n")
            response = RESPONSE_CONSUME
            self.scene.pane.tool_active = False
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        return response
