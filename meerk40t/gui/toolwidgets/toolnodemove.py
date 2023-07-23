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

        pos = complex(*space_pos[:2])
        points = self.scene.context.elements.points

        if event_type == "leftdown":
            offset = 5
            try:
                offset /= math.sqrt(
                    abs(self.scene.widget_root.scene_widget.matrix.determinant)
                )
            except ZeroDivisionError:
                pass
            points.clear()
            for node in self.scene.context.elements.flat(emphasized=True):
                if not hasattr(node, "geometry"):
                    continue
                geom = node.geometry
                for idx, s in geom.near(pos, offset):
                    points.append((geom.segments[idx], idx, s, node, geom))
            if not points:
                return RESPONSE_DROP
            return RESPONSE_CONSUME
        if event_type == "move":
            for s, idx, n, s_node, s_geom in points:
                s[n] = pos
                s_node.altered()
            return RESPONSE_CONSUME
        if event_type == "leftup":
            return RESPONSE_CONSUME
        return RESPONSE_CHAIN
