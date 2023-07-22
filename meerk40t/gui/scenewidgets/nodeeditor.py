"""
Affinemover is a replacement for SelectionWidget. It performs the selected widget manipulations toggling itself in
place of the selectionwidget when `affinemover` console command is called. It's generally unusable but performs all
affine transformations on selected objects by moving three points either locked, mirrored, or anchored.
"""
import math

import wx

from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
)
from meerk40t.gui.scene.widget import Widget


class NodeEditor(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)

        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.BLUE)
        self._bounds = None
        self.point_1 = None
        self.point_2 = None
        self.point_4 = None
        self._matrix = None
        self._last_m = None
        self._locked_point = None
        self.lock_1 = 0
        self.lock_2 = 0
        self.lock_4 = 0

    def init(self, context):
        context.listen("emphasized", self.emphasis_changed)
        # Option to draw selection Handle outside of box to allow for better visibility

    def final(self, context):
        context.unlisten("emphasized", self.emphasis_changed)

    def emphasis_changed(self, origin, *arg):
        self._bounds = None

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s

        gc.SetPen(wx.BLUE_PEN)
        for node in self.scene.context.elements.flat(emphasized=True):
            if not hasattr(node, "as_geometry"):
                continue
            geom = node.as_geometry()
            from meerk40t.tools.geomstr import Geomstr
            if isinstance(geom, Geomstr):
                for g in geom.as_points():
                    if g is None:
                        continue
                    ptx = g.real
                    pty = g.imag
                    gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)

    def hit(self):
        return HITCHAIN_DELEGATE
