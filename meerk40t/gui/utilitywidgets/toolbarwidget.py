from meerk40t.gui.scene.sceneconst import ORIENTATION_CENTERED, ORIENTATION_HORIZONTAL
from meerk40t.gui.scene.widget import Widget


class ToolbarWidget(Widget):
    def __init__(self, scene, left, top, **kwargs):
        Widget.__init__(self, scene, left, top, left, top, **kwargs)
        self.properties = ORIENTATION_CENTERED | ORIENTATION_HORIZONTAL
