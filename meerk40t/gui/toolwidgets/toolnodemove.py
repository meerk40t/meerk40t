from meerk40t.gui.toolwidgets.toolwidget import ToolWidget


class NodeMoveTool(ToolWidget):
    """
    Node Move Tool allows clicking and dragging of nodes to new locations.
    """
    select_mode = "vertex_editor"

    def __init__(self, scene):
        ToolWidget.__init__(self, scene)
