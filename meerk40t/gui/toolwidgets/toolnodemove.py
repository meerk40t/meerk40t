import math

from meerk40t.gui.scene.sceneconst import (
    RESPONSE_DROP,
    RESPONSE_CONSUME,
    RESPONSE_CHAIN,
)
from meerk40t.gui.toolwidgets.toolwidget import ToolWidget


class NodeMoveTool(ToolWidget):
    """
    Node Move Tool allows clicking and dragging of nodes to new locations.
    """

    select_mode = "vertex"

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)

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
        try:
            pos = complex(*space_pos[:2])
        except TypeError:
            return RESPONSE_CONSUME
        points = self.scene.context.elements.points

        if event_type == "leftdown":
            offset = 5000
            points.clear()
            for node in self.scene.context.elements.flat(emphasized=True):
                if not hasattr(node, "as_geometry"):
                    continue
                geom_transformed = node.as_geometry()
                for index_line, index_pos in geom_transformed.near(pos, offset):
                    points.append([index_line, index_pos, geom_transformed, node])
            if not points:
                return RESPONSE_DROP
            return RESPONSE_CONSUME
        if event_type == "move":
            for data in points:
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
                    for p in points:
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
        return RESPONSE_CHAIN
