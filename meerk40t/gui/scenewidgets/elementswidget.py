from math import sqrt

from meerk40t.core.units import Length
from meerk40t.gui.laserrender import DRAW_MODE_EDIT, DRAW_MODE_REGMARKS
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
            Length.units_per_spx = zoom_scale
        except ZeroDivisionError:
            matrix.reset()
            zoom_scale = 1
        if zoom_scale < 1:
            zoom_scale = 1
        win_x_max, win_y_max = self.scene.gui.ClientSize
        win_x_min = 0
        win_y_min = 0
        xmin = float("inf")
        ymin = float("inf")
        xmax = -float("inf")
        ymax = -float("inf")
        # look at the four edges as we could be rotated / inverted etc.
        for x in (win_x_min, win_x_max):
            for y in (win_y_min, win_y_max):
                win_pos = (x, y)
                scene_pos = self.scene.convert_window_to_scene(win_pos)
                xmin = min(xmin, scene_pos[0])
                xmax = max(xmax, scene_pos[0])
                ymin = min(ymin, scene_pos[1])
                ymax = max(ymax, scene_pos[1])
        # Set visible area
        box = (xmin, ymin, xmax, ymax)
        self.renderer.set_visible_area(box)
        draw_mode = self.renderer.context.draw_mode
        if (draw_mode & DRAW_MODE_REGMARKS) == 0:
            # Very faint in the background as orientation - alpha 64
            self.renderer.render(
                context.elements.regmarks_nodes(selected=False),
                gc,
                draw_mode,
                zoomscale=zoom_scale,
                alpha=32,
                msg="regmarks unselected",
            )
            self.renderer.render(
                context.elements.regmarks_nodes(selected=True),
                gc,
                draw_mode,
                zoomscale=zoom_scale,
                alpha=64,
                msg="regmarks selected",
            )
            # Slightly more prominent - alpha 96
            self.renderer.render(
                context.elements.placement_nodes(),
                gc,
                draw_mode,
                zoomscale=zoom_scale,
                alpha=96,
                msg="placement node",
            )
        if self.scene.pane.tool_container.mode == "vertex":
            draw_mode |= DRAW_MODE_EDIT
        self.renderer.render(
            context.elements.elems_nodes(),
            gc,
            draw_mode,
            zoomscale=zoom_scale,
            msg="elements",
        )

    def event(
        self, window_pos=None, space_pos=None, event_type=None, modifiers=None, **kwargs
    ):
        # Cover some unlikely crashes...
        try:
            elements = self.scene.context.elements
            if elements is None:
                return
        except TypeError:
            return
        empty_or_right = True
        if modifiers is not None:
            for mod in modifiers:
                if mod == "m_right":
                    continue
                empty_or_right = False
                break

        if event_type == "rightdown" and empty_or_right:
            if not self.scene.pane.tool_active:
                if self.scene.pane.active_tool != "none":
                    self.scene.context("tool none\n")
                    return RESPONSE_CONSUME
                else:
                    self.scene.context.signal("scene_right_click")
                    return RESPONSE_CONSUME
        elif event_type == "rightdown":  # any modifier
            # if self.scene.context.use_toolmenu:
            #     self.scene.context("tool_menu")
            #     return RESPONSE_CONSUME
            return RESPONSE_CHAIN
        elif event_type == "leftclick":
            if self.scene.pane.modif_active:
                return RESPONSE_CHAIN
            keep_old = "shift" in modifiers
            smallest = bool(self.scene.context.select_smallest) != bool(
                "ctrl" in modifiers
            )
            elements.set_emphasized_by_position(space_pos, keep_old, smallest)
            elements.signal("select_emphasized_tree", 0)
            return RESPONSE_CONSUME
        return RESPONSE_DROP
