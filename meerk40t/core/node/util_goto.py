from meerk40t.core.cutcode.gotocut import GotoCut
from meerk40t.core.elements.element_types import op_nodes
from meerk40t.core.node.node import Node


class GotoOperation(Node):
    """
    GotoOperation tells the controller to return to origin.

    Node type "util goto"
    """

    def __init__(self, **kwargs):
        self.output = True
        self.x = 0.0
        self.y = 0.0
        self.absolute = False
        super().__init__(type="util goto", **kwargs)
        self._formatter = "{enabled}{element_type} {absolute}{x} {y} "

    def __repr__(self):
        return f"GotoOperation('{self.x}, {self.y}')"

    def __len__(self):
        return 1

    @property
    def implicit_passes(self):
        return 1

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
        origin = self.x == 0 and self.y == 0
        default_map["element_type"] = "Origin" if origin else "Goto"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["adjust"] = f" ({self.x}, {self.y})" if not origin else ""
        default_map.update(self.__dict__)
        default_map["absolute"] = "=" if self.absolute else ""
        return default_map

    def can_drop(self, drag_node):
        # Move operation to a different position.
        return bool(drag_node.type in op_nodes)

    def drop(self, drag_node, modify=True, flag=False):
        # Default routine for drag + drop for an op node - irrelevant for others...
        drop_node = self
        if not self.can_drop(drag_node):
            return False
        if modify:
            drop_node.insert_sibling(drag_node)
        return True

    def preprocess(self, context, matrix, plan):
        """
        Preprocess util goto

        @param context:
        @param matrix:
        @param plan: Plan value during preprocessor call
        @return:
        """
        self.x, self.y = context.space.display.position(
            self.x, self.y, vector=not self.absolute
        )
        if self.absolute:
            self.x, self.y = matrix.point_in_matrix_space((self.x, self.y))
        else:
            self.x, self.y = matrix.transform_vector([self.x, self.y])

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for a raster operation. This takes any image node children
        and converts them into rastercut objects. These objects should have already been converted
        from vector shapes.

        The preference for raster shapes is to use the settings set on this operation rather than on the image-node.
        """
        cut = GotoCut((self.x, self.y))
        cut.original_op = self.type
        yield cut

    def generate(self):
        yield "move_abs", self.x, self.y
