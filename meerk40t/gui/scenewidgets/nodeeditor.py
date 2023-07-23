"""
Node editor is a selection tool with node moving capabilities.
"""

import math

import wx

from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.scene.widget import Widget


class NodeEditor(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
        self.tool_pen = wx.Pen()
        self.tool_pen.SetColour(wx.BLUE)
        self._select_points = []
        self._emphasized = []

    def init(self, context):
        context.listen("emphasized", self.emphasis_changed)
        # Option to draw selection Handle outside of box to allow for better visibility

    def final(self, context):
        context.unlisten("emphasized", self.emphasis_changed)

    def emphasis_changed(self, origin, *arg):
        self._emphasized = list(self.scene.context.elements.flat(emphasized=True))
        self._select_points.clear()

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        modifiers=None,
        keycode=None,
        **kwargs,
    ):
        """
        The routine dealing with propagated scene events

        Args:
            window_pos (tuple): The coordinates of the mouse position in window coordinates
            space_pos (tuple): The coordinates of the mouse position in scene coordinates
            event_type (string): [description]. Defaults to None.
            nearest_snap (tuple, optional): If set the coordinates of the nearest snap point in scene coordinates.
            modifiers (string): If available provides a  list of modifier keys that were pressed (shift, alt, ctrl).
            keycode (string): if available the keyocde that was pressed

        Returns:
            Indicator how to proceed with this event after its execution (consume, chain etc)
        """

        pos = complex(*space_pos[:2])

        if event_type == "leftdown":
            offset = 5
            try:
                offset /= math.sqrt(
                    abs(self.scene.widget_root.scene_widget.matrix.determinant)
                )
            except ZeroDivisionError:
                pass
            self._select_points.clear()
            for node in self._emphasized:
                if not hasattr(node, "geometry"):
                    continue
                geom = node.geometry
                for idx, g in enumerate(geom.segments):
                    if abs(pos - g[0]) < offset:
                        self._select_points.append((g, idx, 0, node, geom))
                    if abs(pos - g[-1]) < offset:
                        self._select_points.append((g, idx, -1, node, geom))
            if not self._select_points:
                return RESPONSE_DROP
            return RESPONSE_CONSUME
        if event_type == "move":
            for s, idx, n, s_node, s_geom in self._select_points:
                s[n] = pos
                s_node.altered()
            return RESPONSE_CONSUME
        if event_type == "leftup":
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN

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

        for node in self._emphasized:
            if not hasattr(node, "as_geometry"):
                continue
            geom = node.as_geometry()
            for g in geom.as_points():
                if g is None:
                    continue
                selected = False
                for s, idx, n, s_node, s_geom in self._select_points:
                    if s[n] == g:
                        selected = True
                        break
                if selected:
                    gc.SetPen(wx.RED_PEN)
                else:
                    gc.SetPen(self.tool_pen)
                ptx = g.real
                pty = g.imag
                gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)

    def hit(self):
        return HITCHAIN_HIT
