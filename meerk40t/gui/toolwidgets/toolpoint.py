import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Matrix, Point


class PointTool(ToolWidget):
    """
    Point Drawing Tool.

    Adds points with clicks.
    """

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)

    def process_draw(self, gc: wx.GraphicsContext):
        pass

    def end_tool(self, force=False):
        self.scene.context.signal("statusmsg", "")
        self.scene.request_refresh()
        if force or self.scene.context.just_a_single_element:
            self.scene.pane.tool_active = False
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
        if event_type == "leftclick":
            if nearest_snap is None:
                sx, sy = self.scene.get_snap_point(
                    space_pos[0], space_pos[1], modifiers
                )
                point = Point(sx, sy)
            else:
                point = Point(nearest_snap[0], nearest_snap[1])
            elements = self.scene.context.elements
            # _("Create point")
            with elements.undoscope("Create point"):
                node = elements.elem_branch.add(
                    point=point,
                    matrix=Matrix(),
                    type="elem point",
                    stroke_width=elements.default_strokewidth,
                    stroke=elements.default_stroke,
                    fill=elements.default_fill,
                )
                if elements.classify_new:
                    elements.classify([node])
            self.notify_created(node)
            self.end_tool()
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape") or event_type == "rightdown":
            if self.scene.pane.tool_active:
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.end_tool(force=True)
        return response
