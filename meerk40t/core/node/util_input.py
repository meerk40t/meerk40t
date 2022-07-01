from meerk40t.core.cutcode import InputCut, OutputCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class InputOperation(Node):
    """
    InputOperation sets GPIO values.

    Node type "util input"
    """

    def __init__(self, mask=0, value=0, message=None, **kwargs):
        super().__init__(type="util input", **kwargs)
        self.settings = {
            "input_mask": mask,
            "input_value": value,
            "input_message": message,
            "output": True,
        }

    def __repr__(self):
        return f"InputOperation('{self.mask}')"

    def __str__(self):
        parts = list()
        if not self.output:
            parts.append("(Disabled)")
        parts.append("Input")
        parts.append(self.bitstring())
        return " ".join(parts)

    def __copy__(self):
        return InputOperation(self.mask, self.value, self.message)

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

    @property
    def mask(self):
        return int(self.settings.get("input_mask"))

    @mask.setter
    def mask(self, v):
        self.settings["input_mask"] = v

    @property
    def value(self):
        return int(self.settings.get("input_value"))

    @value.setter
    def value(self, v):
        self.settings["input_value"] = v

    @property
    def message(self):
        return str(self.settings.get("input_message"))

    @message.setter
    def message(self, v):
        self.settings["input_message"] = v

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
        default_map = super(InputOperation, self).default_map(default_map=default_map)
        default_map["element_type"] = "Input"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["mask"] = self.mask
        default_map["value"] = self.value
        default_map["message"] = self.message
        default_map["bits"] = self.bitstring()
        default_map.update(self.settings)
        return default_map

    def drop(self, drag_node):
        drop_node = self
        if drag_node.type in op_nodes:
            drop_node.insert_sibling(drag_node)
            return True
        elif drop_node.type == "branch ops":
            # Dragging operation to op branch to effectively move to bottom.
            drop_node.append_child(drag_node)
            return True
        return False

    def load(self, settings, section):
        update_dict = settings.read_persistent_string_dict(section, suffix=True)
        self.settings.update(update_dict)

    def save(self, settings, section):
        settings.write_persistent_dict(section, self.settings)

    def as_cutobjects(self, closed_distance=15, passes=1):
        """
        Generator of cutobjects for a raster operation. This takes any image node children
        and converts them into rastercut objects. These objects should have already been converted
        from vector shapes.

        The preference for raster shapes is to use the settings set on this operation rather than on the image-node.
        """
        input = InputCut(self.mask, self.value, self.message)
        input.original_op = self.type
        yield input
