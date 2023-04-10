import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Point

_ = wx.GetTranslation

class PlacementTool(ToolWidget):
    """
    Placement Tool.

    Adds a placement with clicks.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.has_ctrl = False
        self.has_alt = False
        self.has_shift = False
        self.message_displayed = ""
        self.scene.context.signal("statusmsg", self.message_displayed)

    def process_draw(self, gc: wx.GraphicsContext):
        pass

    def done(self):
        self.scene.pane.tool_active = False
        self.scene.request_refresh()
        self.message_displayed = ""
        self.scene.context("tool none\n")

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        **kwargs,
    ):
        response = RESPONSE_CHAIN
        if (
            modifiers is None
            or (event_type == "key_up" and "alt" in modifiers)
            or ("alt" not in modifiers)
        ):
            self.has_alt = False
        else:
            self.has_alt = True
        if (
            modifiers is None
            or (event_type == "key_up" and "ctrl" in modifiers)
            or ("ctrl" not in modifiers)
        ):
            self.has_ctrl = False
        else:
            self.has_ctrl = True
        if (
            modifiers is None
            or (event_type == "key_up" and "shift" in modifiers)
            or ("shift" not in modifiers)
        ):
            self.has_shift = False
        else:
            self.has_shift = True

        if event_type == "leftclick":
            print (f"Ctrl={self.has_ctrl}, alt={self.has_alt}, shift={self.has_shift}, point={space_pos}, snap={nearest_snap}")
            if nearest_snap is None:
                point = Point(space_pos[0], space_pos[1])
            else:
                point = Point(nearest_snap[0], nearest_snap[1])
            if self.has_ctrl:
                corner = 2 # Bottom Right
            elif self.has_shift:
                corner = 4 # Center
            else:
                corner = 0 # Top Left
            elements = self.scene.context.elements
            node = elements.op_branch.add(
                type="place point",
                x=point.x,
                y=point.y,
                rotation = 0,
                corner=corner,
            )
            self.notify_created(node)
            self.done()
            response = RESPONSE_CONSUME
        elif event_type in ("leftdown", "hover_start", "hover"):
            if self.message_displayed == "":
                self.message_displayed = _(
                    "Click to set the TL-corner of the job (Ctrl for BR, Shift for Center)"
                    )
                self.scene.context.signal("statusmsg", self.message_displayed)
            self.scene.pane.tool_active = True
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.pane.tool_active:
                self.done()
                response = RESPONSE_CONSUME
        return response
