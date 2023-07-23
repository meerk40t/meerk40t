"""
Node editor is a selection tool with node moving capabilities.
"""

import math

import wx

from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_DELEGATE,
)
from meerk40t.gui.scene.widget import Widget


class NodeSelector(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.BLUE)
        self._emphasized = []

    def init(self, context):
        context.listen("emphasized", self.emphasis_changed)
        # Option to draw selection Handle outside of box to allow for better visibility

    def final(self, context):
        context.unlisten("emphasized", self.emphasis_changed)

    def emphasis_changed(self, origin, *arg):
        self._emphasized = list(self.scene.context.elements.flat(emphasized=True))
        self.scene.context.elements.points.clear()

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        if not self._emphasized:
            return
        offset = 5
        try:
            offset /= math.sqrt(
                abs(self.scene.widget_root.scene_widget.matrix.determinant)
            )
        except ZeroDivisionError:
            pass

        points = self.scene.context.elements.points
        for node in self._emphasized:
            if not hasattr(node, "as_geometry"):
                continue
            geom = node.as_geometry()
            for g in geom.as_points():
                if g is None:
                    continue
                selected = False
                for s, idx, n, s_node, s_geom in points:
                    if s[n] == g:
                        selected = True
                        break
                if selected:
                    gc.SetPen(wx.RED_PEN)
                    gc.SetBrush(wx.TRANSPARENT_BRUSH)
                else:
                    gc.SetPen(self.tool_pen)
                    gc.SetBrush(wx.TRANSPARENT_BRUSH)
                ptx = g.real
                pty = g.imag
                gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)

    def hit(self):
        return HITCHAIN_DELEGATE
