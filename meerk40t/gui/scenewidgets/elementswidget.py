from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CONSUME, RESPONSE_DROP
from meerk40t.gui.scene.widget import Widget


class ElementsWidget(Widget):
    """
    The ElementsWidget is tasked with drawing the elements within the scene. It also
    serve to process leftclick in order to emphasize the given object.
    """

    def __init__(self, scene, renderer):
        Widget.__init__(self, scene, all=True)
        self.renderer = renderer

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc):
        context = self.scene.context
        matrix = self.scene.widget_root.scene_widget.matrix
        scale_x = matrix.value_scale_x()
        try:
            zoom_scale = 1 / scale_x
        except ZeroDivisionError:
            matrix.reset()
            zoom_scale = 1
        if zoom_scale < 1:
            zoom_scale = 1
        self.renderer.render(
            context.elements.elems_nodes(),
            gc,
            self.renderer.context.draw_mode,
            zoomscale=zoom_scale,
        )

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "leftclick":
            elements = self.scene.context.elements
            elements.set_emphasized_by_position(space_pos)
            elements.signal("select_emphasized_tree", 0)
            return RESPONSE_CONSUME
        return RESPONSE_DROP
