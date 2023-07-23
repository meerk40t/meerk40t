"""
Node selector stub
"""

from meerk40t.gui.scene.widget import Widget


class NodeSelector(Widget):
    def __init__(self, scene):
        Widget.__init__(self, scene, all=True)
