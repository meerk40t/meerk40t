from math import sqrt

from meerk40t.gui.laserrender import DRAW_MODE_REGMARKS
from meerk40t.gui.scene.sceneconst import (
    HITCHAIN_HIT,
    RESPONSE_CHAIN,
    RESPONSE_CONSUME,
    RESPONSE_DROP,
)
from meerk40t.gui.scene.widget import Widget


class ElementsWidget(Widget):
    """
    The ElementsWidget is tasked with drawing the elements within the scene. It also
    serves to process leftclick in order to emphasize the given object.
    """

    def __init__(self, scene, renderer):
        Widget.__init__(self, scene, all=True)
        self.renderer = renderer

    def hit(self):
        return HITCHAIN_HIT

    def process_draw(self, gc):
        context = self.scene.context
        matrix = self.scene.widget_root.scene_widget.matrix
        scale_x = sqrt(abs(matrix.determinant))
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
                context.elements.placement_nodes(),
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

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):

        if event_type == "rightdown" and not modifiers:
            if not self.scene.pane.tool_active:
                if self.scene.pane.active_tool != "none":
                    self.scene.context("tool none")
                    return RESPONSE_CONSUME
                else:
                    self.scene.context.signal("scene_right_click")
                    return RESPONSE_CONSUME
        elif event_type == "rightdown":  # any modifier
            if self.scene.context.use_toolmenu:
                self.scene.context("tool_menu")
                return RESPONSE_CONSUME
            return RESPONSE_CHAIN
        elif event_type == "leftclick":
            elements = self.scene.context.elements
            keep_old = "shift" in modifiers
            smallest = bool(self.scene.context.select_smallest) != bool(
                "ctrl" in modifiers
            )
            elements.set_emphasized_by_position(space_pos, keep_old, smallest)
            elements.signal("select_emphasized_tree", 0)
            return RESPONSE_CONSUME
        return RESPONSE_DROP
