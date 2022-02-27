import wx

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
            gc.SetPen(wx.BLUE_PEN)
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
        if event_type == "leftclick":
            if self.path is None:
                self.path = Path(stroke="blue")
                self.path.move((space_pos[0], space_pos[1]))
            else:
                self.path.line((space_pos[0], space_pos[1]))
            self.c0 = None
            print(self.path.d())
        elif event_type == "rightdown":
            self.path = None
            self.mouse_position = None
            self.scene.context.signal("refresh_scene", self.scene.name)
        elif event_type == "leftdown":
            self.c0 = (space_pos[0], space_pos[1])
        elif event_type == "move":
            self.c0 = (space_pos[0], space_pos[1])
            if self.path:
                self.scene.context.signal("refresh_scene", self.scene.name)
        elif event_type == "leftup":
            if self.c0 is not None and self.path:
                self.path.smooth_cubic(self.c0, self.mouse_position)
                self.scene.context.signal("refresh_scene", self.scene.name)
            self.c0 = None
            self.mouse_position = None
        elif event_type == "hover":
            self.mouse_position = space_pos[0], space_pos[1]
            if self.path:
                self.scene.context.signal("refresh_scene", self.scene.name)
        elif event_type == "doubleclick":
            t = self.path
            if len(t) != 0:
                self.scene.context.elements.add_elem(t, classify=True)
            self.path = None
            self.mouse_position = None
