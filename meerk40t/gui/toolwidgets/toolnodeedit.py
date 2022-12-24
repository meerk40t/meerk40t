import wx

from meerk40t.gui.laserrender import swizzlecolor
from meerk40t.gui.scene.sceneconst import (
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
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

    def calculate_points(self):
        self.nodes = []
        offset = 5000
        selected_node = self.scene.context.elements.first_element()
        try:
            path = selected_node.path
        except AttributeError:
            return
        for segment in path:
            q = type(segment).__name__
            if q in ("Line", "Close"):
                # self.nodes.append(
                #     (
                #         segment.start.x - offset,
                #         segment.start.y - offset,
                #         offset * 2,
                #         offset * 2,
                #         segment,
                #         segment.start,
                #     )
                # )
                self.nodes.append(
                    (
                        segment.end.x - offset,
                        segment.end.y - offset,
                        offset * 2,
                        offset * 2,
                        selected_node,
                        segment,
                        segment.end,
                    )
                )
            elif q == "Move":
                self.nodes.append(
                    (
                        segment.end.x - offset,
                        segment.end.y - offset,
                        offset * 2,
                        offset * 2,
                        selected_node,
                        segment,
                        segment.end,
                    )
                )
            elif q == "QuadraticBezier":
                # self.nodes.append(
                #     (
                #         segment.start.x - offset,
                #         segment.start.y - offset,
                #         offset * 2,
                #         offset * 2,
                #         segment,
                #         segment.start,
                #     )
                # )
                self.nodes.append(
                    (
                        segment.control.x - offset,
                        segment.control.y - offset,
                        offset * 2,
                        offset * 2,
                        selected_node,
                        segment,
                        segment.control,
                    )
                )
                self.nodes.append(
                    (
                        segment.end.x - offset,
                        segment.end.y - offset,
                        offset * 2,
                        offset * 2,
                        selected_node,
                        segment,
                        segment.end,
                    )
                )
            elif q == "CubicBezier":
                # self.nodes.append(
                #     (
                #         segment.start.x - offset,
                #         segment.start.y - offset,
                #         offset * 2,
                #         offset * 2,
                #         segment,
                #         segment.start,
                #     )
                # )
                self.nodes.append(
                    (
                        segment.control1.x - offset,
                        segment.control1.y - offset,
                        offset * 2,
                        offset * 2,
                        selected_node,
                        segment,
                        segment.control1,
                    )
                )
                self.nodes.append(
                    (
                        segment.control2.x - offset,
                        segment.control2.y - offset,
                        offset * 2,
                        offset * 2,
                        selected_node,
                        segment,
                        segment.control2,
                    )
                )
                self.nodes.append(
                    (
                        segment.end.x - offset,
                        segment.end.y - offset,
                        offset * 2,
                        offset * 2,
                        selected_node,
                        segment,
                        segment.end,
                    )
                )

    def process_draw(self, gc: wx.GraphicsContext):
        if not self.nodes:
            self.calculate_points()
        gc.SetPen(self.pen)
        for x, y, w, h, node, segment, point in self.nodes:
            gc.DrawRectangle(x, y, w, h)

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        offset = 5000
        response = RESPONSE_CHAIN
        if event_type == "leftdown":
            self.pen = wx.Pen()
            self.pen.SetColour(
                wx.Colour(swizzlecolor(self.scene.context.elements.default_stroke))
            )
            self.pen.SetWidth(1000)
            xp = space_pos[0]
            yp = space_pos[1]
            if self.nodes:
                for i, n in enumerate(self.nodes):
                    x, y, w, h, node, segment, point = n
                    if x <= xp <= x + w and y <= yp <= y + h:
                        self.selected_index = i
                        break
                else:  # For-else == icky
                    self.selected_index = None
            response = RESPONSE_CONSUME
        elif event_type == "move":
            if not self.selected_index:
                self.scene.request_refresh()
                return RESPONSE_CONSUME
            current_node = self.nodes[self.selected_index]
            x, y, w, h, node, segment, point = current_node
            point.x += space_pos[4]
            point.y += space_pos[5]

            self.nodes[self.selected_index] = (
                point.x - offset,
                point.y - offset,
                offset * 2,
                offset * 2,
                node,
                segment,
                point,
            )
            node.altered()
            self.scene.request_refresh()
            response = RESPONSE_CONSUME
        elif event_type == "lost" or (event_type == "key_up" and modifiers == "escape"):
            if self.scene.tool_active:
                self.scene.tool_active = False
                self.scene.request_refresh()
                response = RESPONSE_CONSUME
            else:
                response = RESPONSE_CHAIN
        elif event_type == "leftup":
            response = RESPONSE_CONSUME
        return response
