import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Matrix, Point, Polyline


class PointTool(ToolWidget):
    """
    Point Drawing Tool.

    Adds points with clicks.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)

    def process_draw(self, gc: wx.GraphicsContext):
        pass

    def event(
        self, window_pos=None, space_pos=None, event_type=None, nearest_snap=None
    ):
        response = RESPONSE_CHAIN
        if event_type == "leftclick":
            if nearest_snap is None:
                point = Point(space_pos[0], space_pos[1])
            else:
                point = Point(nearest_snap[0], nearest_snap[1])
            elements = self.scene.context.elements
            node = elements.elem_branch.add(
                point=point, matrix=Matrix(), type="elem point"
            )
            if self.scene.context.elements.default_stroke is not None:
                node.stroke = self.scene.context.elements.default_stroke
            if self.scene.context.elements.default_fill is not None:
                node.fill = self.scene.context.elements.default_fill
            if elements.classify_new:
                elements.classify([node])
            self.notify_created(node)
            response = RESPONSE_CONSUME
        return response
