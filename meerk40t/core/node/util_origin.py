from meerk40t.core.cutcode.setorigincut import SetOriginCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class SetOriginOperation(Node):
    """
    SetOriginOperation tells the controller to return to origin.

    Node type "util origin"
    """

    def __init__(self, x=None, y=None, **kwargs):
        super().__init__(type="util origin", **kwargs)
        self.settings = {"x": x, "y": y, "output": True}
        self._formatter = "{enabled}{element_type} {x} {y}"

    def __repr__(self):
        return f"SetOriginOperation('{self.x}, {self.y}')"

    def __copy__(self):
        return SetOriginOperation(self.x, self.y)

    def __len__(self):
        return 1

    def validate(self):
        parameters = [
            ("output", lambda v: str(v).lower() == "true"),
            ("x", float),
            ("y", float),
        ]
        settings = self.settings
        for param, cast in parameters:
            try:
                if param in settings and settings[param] is not None:
                    settings[param] = (
                        cast(settings[param]) if settings[param] != "None" else None
                    )
            except (KeyError, ValueError):
                pass

    @property
    def x(self):
        return self.settings.get("x")

    @x.setter
    def x(self, v):
        self.settings["x"] = v

    @property
    def y(self):
        return self.settings.get("y")

    @y.setter
    def y(self, v):
        self.settings["y"] = v

    @property
    def output(self):
        return self.settings.get("output", True)

    @output.setter
    def output(self, v):
        self.settings["output"] = v

    @property
    def implicit_passes(self):
        return 1

    def default_map(self, default_map=None):
        default_map = super(SetOriginOperation, self).default_map(
            default_map=default_map
        )
        default_map["element_type"] = "SetOrigin"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["adjust"] = (
            f" ({self.x}, {self.y})"
            if self.x is not None and self.y is not None
            else "<Current>"
        )
        default_map["x"] = self.x
        default_map["y"] = self.y
        default_map.update(self.settings)
        return default_map

    def drop(self, drag_node, modify=True):
        drop_node = self
        if drag_node.type in op_nodes:
            if modify:
                drop_node.insert_sibling(drag_node)
            return True
        elif drop_node.type == "branch ops":
            # Dragging operation to op branch to effectively move to bottom.
            if modify:
                drop_node.append_child(drag_node)
            return True
        return False

    def load(self, settings, section):
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)
        self.validate()

    def save(self, settings, section):
        settings.write_persistent_dict(section, self.settings)

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for a raster operation. This takes any image node children
        and converts them into rastercut objects. These objects should have already been converted
        from vector shapes.

        The preference for raster shapes is to use the settings set on this operation rather than on the image-node.
        """
        if self.x is None or self.y is None:
            cut = SetOriginCut()
        else:
            cut = SetOriginCut((self.x, self.y))
        cut.original_op = self.type
        yield cut

    def generate(self):
        yield "set_origin", self.x, self.y
