from copy import copy

from meerk40t.core.node.elem_default import ElemNode


class EllipseNode(ElemNode):
    """
    EllipseNode is the bootstrapped node type for the 'elem ellipse' type.
    """

    def __init__(self, data_object, matrix=None, fill=None, stroke=None, stroke_width=None, **kwargs):
        super(EllipseNode, self).__init__(data_object, matrix=matrix)
        self.fill = fill
        self.stroke = stroke
        self.stroke_width = stroke_width

    def __copy__(self):
        return EllipseNode(copy(self.object))

    def default_map(self, default_map=None):
        default_map = super(EllipseNode, self).default_map(default_map=default_map)
        default_map['element_type'] = "Ellipse"
        return default_map
