"""
Node selector stub
"""
import wx

from meerk40t.gui.scene.widget import Widget


class NodeSelector(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        gc.PushState()
        offset = 2500
        gc.SetPen(wx.RED_PEN)
        gc.SetBrush(wx.RED_BRUSH)
        points = self.scene.context.elements.points
        for data in points:
            index_line, index_pos, geom_t, node = data
            g = geom_t.segments[index_line][index_pos]
            ptx = g.real
            pty = g.imag
            gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)
        gc.PopState()
