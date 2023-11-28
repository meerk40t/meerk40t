from .toolpointlistbuilder import PointListTool


class LineTool(PointListTool):
    """
    Line Drawing Tool.

    Adds Line with two clicks.
    """

    def __init__(self, scene):
        PointListTool.__init__(self, scene)

    def create_node(self):
        if len(self.point_series) > 1:
            x1 = self.point_series[0][0]
            y1 = self.point_series[0][1]
            x2 = self.point_series[1][0]
            y2 = self.point_series[1][1]
            elements = self.scene.context.elements
            node = elements.elem_branch.add(
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                stroke_width=elements.default_strokewidth,
                stroke=elements.default_stroke,
                fill=elements.default_fill,
                type="elem line",
            )
            if elements.classify_new:
                elements.classify([node])
            self.notify_created(node)

    def point_added(self):
        if len(self.point_series) > 1:
            self.end_tool()  # That will call everything
