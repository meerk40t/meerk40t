
import wx

from meerk40t.core.node.elem_path import PathNode
from meerk40t.gui.laserrender import LaserRender
from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path, Ellipse


class BugTool(ToolWidget):
    """
    Ribbon Tool draws new segments by animating some click and press locations.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.step = 0
        self.renderer = LaserRender(scene.context)

    def process_draw(self, gc: wx.GraphicsContext):
        shape = Ellipse(cx=0, cy=0, r=30000, stroke="blue", stroke_width=1000)
        shape *= f"rotate({self.step}deg)"
        shape *= "scale(1,2)"
        self.step += 1
        n = PathNode(path=abs(Path(shape)))
        n.bbox()
        self.renderer.draw_path_node(n, gc, draw_mode=0)

    def tick(self):
        self.scene.request_refresh()
        return True

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        # We don't set tool_active here, as this can't be properly honored...
        # And we don't care about nearest_snap either...
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.scene.animate(self)
            response = RESPONSE_CONSUME
        return response
