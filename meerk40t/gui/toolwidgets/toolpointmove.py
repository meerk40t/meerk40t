import math

import wx

from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget


class PointMoveTool(ToolWidget):
    """
    Node Move Tool allows clicking and dragging of nodes to new locations.
    """

    def __init__(self, scene, mode=None):
        ToolWidget.__init__(self, scene)
        self.points = list()
        self.pt_offset = 5
        self.point_index = []
        self.current_pos = complex(0, 0)

    def process_draw(self, gc: wx.GraphicsContext):
        """
        Widget-Routine to draw the different elements on the provided GraphicContext
        """
        gc.PushState()
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset = self.pt_offset / s
        gc.SetPen(wx.RED_PEN)
        gc.SetBrush(wx.RED_BRUSH)
        for data in self.points:
            index_line, index_pos, geom_t, node = data
            g = geom_t.segments[index_line][index_pos]
            ptx = g.real
            pty = g.imag
            gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)
        gc.PopState()

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
            keycode (string): if available the keycode that was pressed

        Returns:
            Indicator how to proceed with this event after its execution (consume, chain etc.)
        """
        try:
            if nearest_snap is None:
                pos = complex(*space_pos[:2])
            else:
                pos = complex(*nearest_snap[:2])
        except TypeError:
            return RESPONSE_CONSUME
        self.current_pos = pos

        if event_type == "leftdown":
            if not self.points:
                return RESPONSE_DROP
            self.scene.pane.tool_active = True
            self.scene.pane.modif_active = True
            offset = self.pt_offset
            s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
            offset /= s
            xp = space_pos[0]
            yp = space_pos[1]
            self.point_index.clear()
            w = offset * 4
            h = offset * 4
            for idx, data in enumerate(self.points):
                index_line, index_pos, geom_t, node = data
                pt = geom_t.segments[index_line][index_pos]
                ptx = pt.real
                pty = pt.imag
                x = ptx - 2 * offset
                y = pty - 2 * offset
                if x <= xp <= x + w and y <= yp <= y + h:
                    # print("Found point")
                    self.point_index.append(idx)
            return RESPONSE_CONSUME
        if event_type == "move":
            if "m_middle" in modifiers:
                return RESPONSE_CHAIN
            for idx in self.point_index:
                data = self.points[idx]
                index_line, index_pos, geom_t, node = data
                if not hasattr(node, "geometry"):
                    fillrule = None
                    if hasattr(node, "fillrule"):
                        fillrule = node.fillrule
                    new_node = node.replace_node(
                        keep_children=True,
                        stroke=node.stroke,
                        fill=node.fill,
                        stroke_width=node.stroke_width,
                        stroke_scale=node.stroke_scale,
                        fillrule=fillrule,
                        id=node.id,
                        label=node.label,
                        lock=node.lock,
                        type="elem path",
                        geometry=geom_t,
                    )
                    for p in self.points:
                        if p[3] is node:
                            p[3] = new_node
                    node = new_node
                geom_t.segments[index_line][index_pos] = pos
                node.geometry = geom_t
                node.matrix.reset()
                node.altered()
            return RESPONSE_CONSUME
        if event_type == "leftup":
            return RESPONSE_CONSUME
        if event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.pane.tool_active:
                self.scene.pane.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
            self.done()
            return response
        if event_type == "rightdown":
            # We stop
            self.done()
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN

    def reset(self):
        self.points.clear()
        self.point_index.clear()

    def done(self):
        self.scene.pane.tool_active = False
        self.scene.pane.modif_active = False
        self.scene.pane.suppress_selection = False
        self.reset()
        self.scene.context("tool none\n")

    def tool_change(self):
        self.reset()

        for node in self.scene.context.elements.flat(emphasized=True):
            if not hasattr(node, "as_geometry"):
                continue
            geom_transformed = node.as_geometry()
            index = geom_transformed.index
            for seg in range(index):
                # Start and end
                self.points.append([seg, 0, geom_transformed, node])
                self.points.append([seg, 4, geom_transformed, node])
        self.scene.pane.suppress_selection = len(self.points) > 0
        self.scene.request_refresh()

    def signal(self, signal, *args, **kwargs):
        """
        Signal routine for stuff that's passed along within a scene,
        does not receive global signals
        """
        if signal == "tool_changed":
            if len(args[0]) > 1 and args[0][1] == "pointmove":
                self.tool_change()
            else:
                self.reset()
        elif signal == "emphasized":
            self.tool_change()
