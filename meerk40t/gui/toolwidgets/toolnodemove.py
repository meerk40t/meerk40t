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
                if not hasattr(node, "geometry"):
                    continue
                geom_transformed = node.as_geometry()
                geom_original = node.geometry
                matrix = ~node.matrix
                for index_line, index_pos in geom_transformed.near(pos, offset):
                    points.append((index_line, index_pos, geom_transformed, geom_original, node, matrix))
            if not points:
                return RESPONSE_DROP
            return RESPONSE_CONSUME
        if event_type == "move":
            for index_line, index_pos, geom_t, geom_o, node, matrix in points:
                pos_t = complex(
                    pos.real * matrix.a + pos.imag * matrix.c + matrix.e,
                    pos.real * matrix.b + pos.imag * matrix.d + matrix.f,
                )
                geom_o.segments[index_line][index_pos] = pos_t
                node.altered()
            return RESPONSE_CONSUME
        if event_type == "leftup":
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN
