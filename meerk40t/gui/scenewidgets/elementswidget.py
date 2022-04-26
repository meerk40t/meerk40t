import wx

from meerk40t.gui.laserrender import DRAW_MODE_REGMARKS
from meerk40t.gui.scene.sceneconst import HITCHAIN_HIT, RESPONSE_CONSUME, RESPONSE_DROP
from meerk40t.gui.scene.widget import Widget


class ElementsWidget(Widget):
    """
    The ElementsWidget is tasked with drawing the elements within the scene. It also
    serves to process leftclick in order to emphasize the given object.
    """

    def __init__(self, scene, renderer):
        Widget.__init__(self, scene, all=True)
        self.renderer = renderer
        self.key_shift_pressed = False

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
        draw_mode = self.renderer.context.draw_mode
        if (draw_mode & DRAW_MODE_REGMARKS) == 0:
            self.renderer.render(
                context.elements.regmarks_nodes(),
                gc,
                draw_mode,
                zoomscale=zoom_scale,
                alpha=64,
            )
        self.renderer.render(
            context.elements.elems_nodes(),
            gc,
            draw_mode,
            zoomscale=zoom_scale,
        )
        # gc.PushState()
        # gc.SetPen(wx.BLACK_PEN)
        # dif = 500
        # for elemnode in context.elements.elems_nodes(emphasized=True):
        #     for p in elemnode.points:
        #         gc.StrokeLine(p[0] - dif, p[1], p[0] + dif, p[1])
        #         gc.StrokeLine(p[0], p[1] - dif, p[0], p[1] + dif)
        # gc.PopState()

    def event(self, window_pos=None, space_pos=None, event_type=None):
        if event_type == "kb_shift_release":
            if self.key_shift_pressed:
                self.key_shift_pressed = False
        elif event_type == "kb_shift_press":
            if not self.key_shift_pressed:
                self.key_shift_pressed = True
        elif event_type == "leftclick":
            elements = self.scene.context.elements
            keep_old = self.key_shift_pressed
            elements.set_emphasized_by_position(space_pos, keep_old)
            elements.signal("select_emphasized_tree", 0)
            return RESPONSE_CONSUME
        return RESPONSE_DROP
