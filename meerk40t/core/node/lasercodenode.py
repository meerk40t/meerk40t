from meerk40t.core.element_types import op_nodes
from meerk40t.core.node.node import Node


class LaserCodeNode(Node):
    """
    LaserCode is basic command operations. It contains nothing except a list of commands to be executed.

    Node type "lasercode"
    """

    def __init__(self, commands=None, id=None, label=None, lock=False, **kwargs):
        super().__init__(type="lasercode", id=id, label=label, lock=lock, **kwargs)
        self._formatter = "{element_type} {command_count}"
        if "name" in kwargs:
            self._name = kwargs["name"]
        else:
            self._name = "LaserCode"
        self.commands = commands
        self.output = True

    def __repr__(self):
        return f"LaserCode('{self.name}', '{str(self.commands)}')"

    def __copy__(self):
        return LaserCodeNode(
            self.commands, name=self.name, id=self.id, label=self.label, lock=self.lock
        )

    def __len__(self):
        return len(self.commands)

    def _str_commands(self):
        for cmd in self.commands:
            if isinstance(cmd, str):
                yield cmd
            else:
                yield cmd[0]

    def default_map(self, default_map=None):
        default_map = super(LaserCodeNode, self).default_map(default_map=default_map)
        default_map["element_type"] = "LaserCode"
        default_map["command_count"] = str(len(self.commands))
        default_map["commands"] = " ".join(self._str_commands())
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

    def generate(self):
        for cmd in self.commands:
            yield cmd
