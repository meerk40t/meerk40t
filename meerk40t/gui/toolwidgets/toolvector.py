import wx

from meerk40t.gui.scene.sceneconst import RESPONSE_CHAIN, RESPONSE_CONSUME
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget
from meerk40t.svgelements import Path

from ..laserrender import LaserRender


class VectorTool(ToolWidget):
    """
    Path Drawing Tool.

    Adds Path with click and drag.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.start_position = None
        self.path = None
        self.mouse_position = None
        self.render = LaserRender(scene.context)
        self.c0 = None

    def process_draw(self, gc: wx.GraphicsContext):
        if self.path:
            gc.SetPen(self.pen)
            gc.SetBrush(wx.TRANSPARENT_BRUSH)
            path = Path(self.path)
            if self.mouse_position is not None:
                if self.c0:
                    path.smooth_cubic(self.c0, self.mouse_position)
                else:
                    path.line(self.mouse_position)
            gpath = self.render.make_path(gc, path)
            gc.DrawPath(gpath)
            del gpath

    def event(self, window_pos=None, space_pos=None, event_type=None):
        response = RESPONSE_CHAIN

        if event_type == "leftclick":
            self.scene.tool_active = True
            if self.path is None:
                self.path = Path(stroke="blue", stroke_width=1000)
                self.path.move((space_pos[0], space_pos[1]))
            else:
                self.path.line((space_pos[0], space_pos[1]))
            self.c0 = None
            response = RESPONSE_CONSUME
        elif event_type == "rightdown":
            self.scene.tool_active = False
            self.path = None
            self.mouse_position = None
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "leftdown":
            self.scene.tool_active = True
            self.c0 = (space_pos[0], space_pos[1])
            response = RESPONSE_CONSUME
        elif event_type == "move":
            self.c0 = (space_pos[0], space_pos[1])
            if self.path:
                self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "leftup":
            self.scene.tool_active = False
            if self.c0 is not None and self.path:
                self.scene.tool_active = True
                self.path.smooth_cubic(self.c0, self.mouse_position)
                self.scene.request_refresh()
            self.c0 = None
            self.mouse_position = None
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "hover":
            self.mouse_position = space_pos[0], space_pos[1]
            if self.path:
                self.scene.request_refresh()
        elif event_type == "doubleclick":
            self.scene.tool_active = False
            t = self.path
            if len(t) != 0:
                elements = self.scene.context.elements
                node = elements.elem_branch.add(path=t, type="elem path")
                elements.classify([node])
            self.path = None
            self.mouse_position = None
            self.notify_created()
            response = RESPONSE_CONSUME
        elif event_type == "lost":
            self.scene.tool_active = False
        return response
