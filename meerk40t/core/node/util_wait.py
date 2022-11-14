from meerk40t.core.cutcode import WaitCut
from meerk40t.core.element_types import *
from meerk40t.core.node.node import Node


class WaitOperation(Node):
    """
    WaitOperation tells the controller to wait for a specified period of time.

    The units for the wait property is seconds. The waitcut uses milliseconds, as does spooled "wait" lasercode.

    Node type "util wait"
    """

    def __init__(self, wait=1.0, id=None, label=None, lock=False, **kwargs):
        super().__init__(type="util wait", id=id, label=label, lock=lock, **kwargs)
        self.settings = {"wait": wait, "output": True}
        self._formatter = "{enabled}{element_type} {wait}"

    def __repr__(self):
        return f"WaitOperation('{self.wait}')"

    def __copy__(self):
        return WaitOperation(self.wait, id=self.id, label=self.label, lock=self.lock)

    def __len__(self):
        return 1

    def validate(self):
        parameters = [
            ("output", lambda v: str(v).lower() == "true"),
            ("wait", float),
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
    def wait(self):
        return self.settings.get("wait")

    @wait.setter
    def wait(self, v):
        self.settings["wait"] = v

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
        default_map = super(WaitOperation, self).default_map(default_map=default_map)
        default_map["element_type"] = "Wait"
        default_map["enabled"] = "(Disabled) " if not self.output else ""
        default_map["wait"] = self.wait
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
        wait = WaitCut(self.wait * 1000.0)
        wait.original_op = self.type
        yield wait

    def generate(self):
        yield "wait", self.wait * 1000.0
