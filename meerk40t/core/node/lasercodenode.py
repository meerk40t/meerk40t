from meerk40t.core.element_types import op_nodes
from meerk40t.core.node.node import Node


class LaserCodeNode(Node):
    """
    LaserCode is basic command operations. It contains nothing except a list of commands to be executed.

    Node type "lasercode"
    """

    def __init__(self, **kwargs):
        self.commands = None
        self.output = True
        self.label = "LaserCode"
        super().__init__(type="lasercode", **kwargs)
        self._formatter = "{element_type} {command_count}"

    def __repr__(self):
        return f"LaserCode('{self.label}', '{str(self.commands)}')"

    def __len__(self):
        return len(self.commands)

    def _str_commands(self):
        for cmd in self.commands:
            if isinstance(cmd, str):
                yield cmd
            else:
                yield cmd[0]

    def default_map(self, default_map=None):
        default_map = super().default_map(default_map=default_map)
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

    def allow_save(self):
        """
        Returns false to prevent saving of blob types into operations.
        @return:
        """
        return False

    def generate(self):
        yield from self.commands
