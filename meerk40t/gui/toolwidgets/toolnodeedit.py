import math

import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget


class EditTool(ToolWidget):
    """
    Edit tool allows you to view and edit the nodes within the scene.
    """

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
        self.nodes = None
        self.selected_index = None

    def final(self, context):
        self.scene.context.unlisten("emphasized", self.on_emphasized_changed)

    def init(self, context):
        self.scene.context.listen("emphasized", self.on_emphasized_changed)

    def on_emphasized_changed(self, origin, *args):
        self.nodes = None
        self.selected_index = None
        self.calculate_points()

    def calculate_points(self):
        self.nodes = []
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s
        selected_node = self.scene.context.elements.first_element(emphasized=True)
        try:
            path = selected_node.path
        except AttributeError:
            return
        for segment in path:
            q = type(segment).__name__
            if q in ("Line", "Close"):
                self.nodes.append(
                    (
                        segment.end,
                        segment,
                        path,
                        selected_node,
                    )
                )
            elif q == "Move":
                self.nodes.append(
                    (
                        segment.end,
                        segment,
                        path,
                        selected_node,
                    )
                )
            elif q == "QuadraticBezier":
                self.nodes.append(
                    (
                        segment.control,
                        segment,
                        path,
                        selected_node,
                    )
                )
                self.nodes.append(
                    (
                        segment.end,
                        segment,
                        path,
                        selected_node,
                    )
                )
            elif q == "CubicBezier":
                self.nodes.append(
                    (
                        segment.control1,
                        segment,
                        path,
                        selected_node,
                    )
                )
                self.nodes.append(
                    (
                        segment.control2,
                        segment,
                        path,
                        selected_node,
                    )
                )
                self.nodes.append(
                    (
                        segment.end,
                        segment,
                        path,
                        selected_node,
                    )
                )

    def process_draw(self, gc: wx.GraphicsContext):
        if not self.nodes:
            return

        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetPen(self.pen)
        for pt, segment, path, node in self.nodes:
            ptx, pty = node.matrix.point_in_matrix_space(pt)
            gc.DrawEllipse(ptx - offset, pty - offset, offset * 2, offset * 2)

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        offset = 5
        s = math.sqrt(abs(self.scene.widget_root.scene_widget.matrix.determinant))
        offset /= s

        if event_type == "leftdown":
            self.pen = wx.Pen()
            self.pen.SetColour(
                wx.Colour(swizzlecolor(self.scene.context.elements.default_stroke))
            )
            self.pen.SetWidth(1000)
            xp = space_pos[0]
            yp = space_pos[1]
            if self.nodes:
                w = offset * 4
                h = offset * 4
                for i, n in enumerate(self.nodes):
                    pt, segment, path, node = n
                    ptx, pty = node.matrix.point_in_matrix_space(pt)
                    x = ptx - 2 * offset
                    y = pty - 2 * offset
                    if x <= xp <= x + w and y <= yp <= y + h:
                        self.selected_index = i
                        break
                else:  # For-else == icky
                    self.selected_index = None
            return RESPONSE_CONSUME
        elif event_type == "middledown" or event_type == "rightdown":
            return RESPONSE_DROP
        elif event_type == "move":
            if not self.selected_index:
                self.scene.request_refresh()
                return RESPONSE_CONSUME
            current = self.nodes[self.selected_index]
            pt, segment, path, node = current
            m = node.matrix.point_in_inverse_space(space_pos[:2])
            pt.x = m[0]
            pt.y = m[1]
            self.nodes[self.selected_index] = (pt, segment, path, node)
            node.altered()
            self.scene.request_refresh()
            return RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.tool_active:
                self.scene.tool_active = False
                self.scene.request_refresh()
                return RESPONSE_CONSUME
            else:
                return RESPONSE_CHAIN
        elif event_type == "leftup":
            return RESPONSE_CONSUME
        return RESPONSE_DROP
