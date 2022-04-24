from meerk40t.core.node.elem_default import ElemNode
from copy import copy


class RectNode(ElemNode):
    """
    RectNode is the bootstrapped node type for the 'elem rect' type.
    """

    def __init__(self, data_object, matrix=None, fill=None, stroke=None, stroke_width=None,  **kwargs):
        super(RectNode, self).__init__(data_object, matrix=matrix)
        self.fill = fill
        self.stroke = stroke
        self.stroke_width = stroke_width

    def __copy__(self):
        return RectNode(copy(self.object))

    def default_map(self, default_map=None):
        default_map = super(RectNode, self).default_map(default_map=default_map)
        default_map['element_type'] = "Rect"
        return default_map
