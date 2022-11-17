from meerk40t.core.cutcode.outputcut import OutputCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class OutputOperation(Node):
    """
    OutputOperation sets GPIO values.

    Node type "util output"
    """

    def __init__(self, mask=0, value=0, message=None, **kwargs):
        super().__init__(type="util output", **kwargs)
        self._formatter = "{enabled}{element_type} {bits}"
        self.settings = {
            "output_mask": mask,
            "output_value": value,
            "output_message": message,
            "output": True,
        }

    def __repr__(self):
        return f"OutputOperation('{self.mask}')"

    def __copy__(self):
        return OutputOperation(self.mask, self.value, self.message)

    def __len__(self):
        return 1

    def bitstring(self):
        mask = self.mask
        value = self.value
        bits = bytearray(b"X" * 16)
        for m in range(16):
            if (mask >> m) & 1:
                bits[m] = ord("1") if (value >> m) & 1 else ord("0")
        return bits.decode("utf8")

    def validate(self):
        parameters = [
            ("output", lambda v: str(v).lower() == "true"),
            ("output_message", str),
            ("output_value", int),
            ("output_mask", int),
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
    def mask(self):
        return self.settings.get("output_mask")

    @mask.setter
    def mask(self, v):
        self.settings["output_mask"] = v

    @property
    def value(self):
        return self.settings.get("output_value")

    @value.setter
    def value(self, v):
        self.settings["output_value"] = v

    @property
    def message(self):
        return self.settings.get("output_message")

    @message.setter
    def message(self, v):
        self.settings["output_message"] = v

    @property
    def output(self):
        return self.settings.get("output", True)

    @output.setter
    def output(self, v):
        self.settings["output"] = v

    @property
    def implicit_passes(self):
        return 1

    def get_mask(self, bit=None):
        if bit is None:
            return self.mask
        return (self.mask >> bit) & 1

    def get_value(self, bit=None):
        if bit is None:
            return self.value
        return (self.value >> bit) & 1

    def mask_toggle(self, bit):
        self.mask = self.mask ^ (1 << bit)

    def mask_on(self, bit):
        self.mask = self.mask | (1 << bit)

    def mask_off(self, bit):
        self.mask = ~((~self.mask) | (1 << bit))

    def value_toggle(self, bit):
        self.value = self.value ^ (1 << bit)

    def value_on(self, bit):
        self.value = self.value | (1 << bit)

    def value_off(self, bit):
        self.value = ~((~self.value) | (1 << bit))

    def default_map(self, default_map=None):
        default_map = super(OutputOperation, self).default_map(default_map=default_map)
        default_map["element_type"] = "Output"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["mask"] = self.mask
        default_map["value"] = self.value
        default_map["message"] = self.message
        default_map["bits"] = self.bitstring()
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
        output = OutputCut(self.mask, self.value, self.message)
        output.original_op = self.type
        yield output
