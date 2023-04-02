from meerk40t.gui.scene.sceneconst import RESPONSE_ABORT
from meerk40t.gui.utilitywidgets.handlewidget import HandleWidget


class ButtonWidget(HandleWidget):
    """
    ButtonWidget serves as an onscreen button backed by a bitmap that when clicked calls the click() function.
    This is a general scene button widget.
    """

    def __init__(self, scene, left, top, right, bottom, bitmap, clicked):
        super().__init__(scene, left, top, right, bottom, bitmap)
        self.clicked = clicked

    def event(self, window_pos=None, space_pos=None, event_type=None, **kwargs):
        if event_type == "leftdown":
            self.clicked(window_pos=window_pos, space_pos=space_pos)
        return RESPONSE_ABORT
