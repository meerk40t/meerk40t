from .toolpointlistbuilder import PointListTool


class ImageCutTool(PointListTool):
    """
    ImageCut Tool.

    Draws a line with click and drag, uses that line to slice an image.
    """

    def __init__(self, scene, mode=None):
        PointListTool.__init__(self, scene, mode=mode)

    def create_node(self):
        if len(self.point_series) > 1:
            x1 = self.point_series[0][0]
            y1 = self.point_series[0][1]
            x2 = self.point_series[1][0]
            y2 = self.point_series[1][1]
            elements = self.scene.context.elements
            elements(f"image linecut {x1} {y1} {x2} {y2}")

    def point_added(self):
        if len(self.point_series) > 1:
            self.end_tool()  # That will call everything
