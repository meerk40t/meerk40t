import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path, Point


class DrawTool(ToolWidget):
    """
    Draw Tool adds paths that are clicked and drawn within the scene.
    """

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)
        self.preferred_length = 50
        self.series = None
        self.last_position = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.series is not None and len(self.series) > 1:
            gc.SetPen(self.pen)
            gc.StrokeLines(self.series)

    def add_point(self, point):
        if len(self.series):
            last = self.series[-1]
            if Point.distance(last, point) < self.preferred_length:
                return
        self.series.append(point)

    def end_tool(self, force=False):
        self.series = None
        self.scene.context.signal("statusmsg", "")
        self.scene.request_refresh()
        if force or self.scene.context.just_a_single_element:
            self.scene.pane.tool_active = False
            self.scene.context("tool none\n")

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        # We don't set tool_active here, as this can't be properly honored...
        # And we don't care about nearest_snap either...
        response = RESPONSE_CHAIN
        if self.series is None:
            self.series = []
        if event_type == "leftdown":
            self.pen = wx.Pen()
            elements = self.scene.context.elements
            self.pen.SetColour(wx.Colour(swizzlecolor(elements.default_stroke)))
            try:
                self.pen.SetWidth(elements.default_strokewidth)
            except TypeError:
                self.pen.SetWidth(int(elements.default_strokewidth))
            self.add_point(space_pos[:2])
            response = RESPONSE_CONSUME
        elif event_type == "move":
            if self.series is None:
                return RESPONSE_DROP
            self.add_point(space_pos[:2])
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape") or event_type == "rightdown":
            if self.scene.pane.tool_active:
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.end_tool(force=True)
        elif event_type == "leftup":
            try:
                t = Path()
                t.move(self.series[0])
                for m in self.series:
                    t.line(m)
                elements = self.scene.context.elements
                # _("Create path")
                with elements.undoscope("Create path"):
                    node = elements.elem_branch.add(
                        path=t,
                        type="elem path",
                        stroke_width=elements.default_strokewidth,
                        stroke=elements.default_stroke,
                        fill=elements.default_fill,
                    )
                    if elements.classify_new:
                        elements.classify([node])
                self.notify_created(node)
            except IndexError:
                pass
            self.end_tool()
            response = RESPONSE_CONSUME
        return response
