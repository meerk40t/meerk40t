from meerk40t.gui.scene.widget import Widget

from ..scene.scene import Scene
from ..scene.sceneconst import HITCHAIN_HIT
from .circlebrush import CircleBrush


class ToolWidget(Widget):
    """
    AbstractClass for the ToolWidgets
    """

    def __init__(self, scene: Scene):
        Widget.__init__(self, scene, all=True)
        self.brush = CircleBrush()

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc):
        self.brush.draw(gc)
