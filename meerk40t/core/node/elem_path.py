from copy import copy

from meerk40t.core.node.elem_default import ElemNode


class PathNode(ElemNode):
    """
    PathNode is the bootstrapped node type for the 'elem path' type.
    """

    def __init__(self, data_object, matrix=None, fill=None, stroke=None, stroke_width=None, **kwargs):
        super(PathNode, self).__init__(data_object, matrix=matrix)
        self.fill = fill
        self.stroke = stroke
        self.stroke_width = stroke_width

    def __copy__(self):
        return PathNode(copy(self.object))

    def default_map(self, default_map=None):
        default_map = super(PathNode, self).default_map(default_map=default_map)
        element = self.object
        if self.object is not None:
            default_map.update(self.object.values)
        default_map["element_type"] = "Path"
        default_map["stroke"] = element.stroke
        default_map["fill"] = element.fill
        default_map["stroke-width"] = element.stroke_width
        default_map['transform'] = element.transform
        if default_map.get('id'):
            default_map['id'] = element.id
        return default_map
