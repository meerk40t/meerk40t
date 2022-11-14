from math import isinf, isnan

import wx

from meerk40t.gui.scene.sceneconst import (
    BUFFER,
    HITCHAIN_DELEGATE,
    ORIENTATION_ABSOLUTE,
    ORIENTATION_CENTERED,
    ORIENTATION_DIM_MASK,
    ORIENTATION_GRID,
    ORIENTATION_HORIZONTAL,
    ORIENTATION_MODE_MASK,
    ORIENTATION_NO_BUFFER,
    ORIENTATION_RELATIVE,
    ORIENTATION_VERTICAL,
    RESPONSE_CHAIN,
)
from meerk40t.gui.zmatrix import ZMatrix
from meerk40t.svgelements import Matrix


class Widget(list):
    """
    Widgets are drawable, interaction objects within the scene. They have their own space, matrix, orientation, and
    processing of events.
    """

    def __init__(
        self,
        scene,
        left: float = None,
        top: float = None,
        right: float = None,
        bottom: float = None,
        all: bool = False,
        visible: bool = True,
    ):
        """
        All produces a widget of infinite space rather than finite space.
        """
        assert scene.__class__.__name__ == "Scene"
        list.__init__(self)
        self.matrix = Matrix()
        self.scene = scene
        self.parent = None
        self.properties = ORIENTATION_RELATIVE
        self.visible = True
        # If this property is set, then it won't be counted as topmost in the hitchain...
        self.transparent = False
        if all:
            # contains all points
            self.left = -float("inf")
            self.top = -float("inf")
            self.right = float("inf")
            self.bottom = float("inf")
        else:
            # contains no points
            self.left = float("inf")
            self.top = float("inf")
            self.right = -float("inf")
            self.bottom = -float("inf")
        if left is not None:
            self.left = left
        if right is not None:
            self.right = right
        if top is not None:
            self.top = top
        if bottom is not None:
            self.bottom = bottom
        if visible is not None:
            self.visible = visible

    def __str__(self):
        return f"Widget({self.left}, {self.top}, {self.right}, {self.bottom})"

    def __repr__(self):
        return f"{type(self).__name__}({self.left}, {self.top}, {self.right}, {self.bottom})"

    def hit(self):
        """
        Default hit state delegates to child-widgets within the current object.
        """
        return HITCHAIN_DELEGATE

    def draw(self, gc):
        """
        Widget.draw() routine which concat's the widgets matrix and call the process_draw() function.
        """
        # Concat if this is a thing.
        if not self.visible:
            return
        matrix = self.matrix
        gc.PushState()
        if matrix is not None and not matrix.is_identity():
            gc.ConcatTransform(wx.GraphicsContext.CreateMatrix(gc, ZMatrix(matrix)))
        self.process_draw(gc)
        for i in range(len(self) - 1, -1, -1):
            widget = self[i]
            if widget is not None:
                widget.draw(gc)
        gc.PopState()

    def process_draw(self, gc):
        """
        Overloaded function by derived widgets to process the drawing of this widget.
        """
        pass

    def contains(self, x, y=None):
        """
        Query whether the current point is contained within the current widget.
        """
        if y is None:
            y = x.y
            x = x.x
        return (
            self.visible
            and self.left <= x <= self.right
            and self.top <= y <= self.bottom
        )

    def event(
        self,
        window_pos=None,
        space_pos=None,
        event_type=None,
        nearest_snap=None,
        **kwargs,
    ):
        """
        Default event which simply chains the event to the next hittable object.
        """
        return RESPONSE_CHAIN

    def notify_added_to_parent(self, parent):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_added_to_parent(parent)

    def notify_added_child(self, child):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_added_child(child)

    def notify_removed_from_parent(self, parent):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_removed_from_parent(parent)

    def notify_removed_child(self, child):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_removed_child(child)

    def notify_moved_child(self, child):
        """
        Widget notify that calls scene notify.
        """
        self.scene.notify_moved_child(child)

    def add_widget(self, index=-1, widget=None, properties=0):
        """
        Add a widget to the current widget.

        Adds at the particular index according to the properties.

        The properties can be used to trigger particular layouts or properties for the added widget.
        """
        if len(self) == 0:
            last = self
        else:
            last = self[-1]
        if 0 <= index < len(self):
            self.insert(index, widget)
        else:
            self.append(widget)
        widget.parent = self
        self.layout_by_orientation(widget, last, properties)
        self.notify_added_to_parent(self)
        self.notify_added_child(widget)

    def translate(self, dx, dy):
        """
        Move the current widget and all child widgets.
        """
        if dx == 0 and dy == 0:
            return
        if isnan(dx) or isnan(dy) or isinf(dx) or isinf(dy):
            return
        self.translate_loop(dx, dy)

    def translate_loop(self, dx, dy):
        """
        Loop the translation call to all child objects.
        """
        if self.properties & ORIENTATION_ABSOLUTE != 0:
            return  # Do not translate absolute oriented widgets.
        self.translate_self(dx, dy)
        for w in self:
            w.translate_loop(dx, dy)

    def translate_self(self, dx, dy):
        """
        Perform the local translation of the current widget
        """
        self.left += dx
        self.right += dx
        self.top += dy
        self.bottom += dy
        if self.parent is not None:
            self.notify_moved_child(self)

    def union_children_bounds(self, bounds=None):
        """
        Find the bounds of the current widget and all child widgets.
        """
        if bounds is None:
            bounds = [self.left, self.top, self.right, self.bottom]
        else:
            if bounds[0] > self.left:
                bounds[0] = self.left
            if bounds[1] > self.top:
                bounds[1] = self.top
            if bounds[2] < self.right:
                bounds[2] = self.left
            if bounds[3] < self.bottom:
                bounds[3] = self.bottom
        for w in self:
            w.union_children_bounds(bounds)
        return bounds

    @property
    def height(self):
        """
        Height of the current widget.
        """
        return self.bottom - self.top

    @property
    def width(self):
        """
        Width of the current widget.
        """
        return self.right - self.left

    def layout_by_orientation(self, widget, last, properties):
        """
        Perform specific layout based on the properties given.
        ORIENTATION_ABSOLUTE places the widget exactly in the scene.
        ORIENTATION_NO_BUFFER nullifies any buffer between objects being laid out.
        ORIENTATION_RELATIVE lays out the added widget relative to the parent.
        ORIENTATION_GRID lays out the added widget in a DIM_MASK grid.
        ORIENTATION_VERTICAL lays the added widget below the reference widget.
        ORIENTATION_HORIZONTAL lays the added widget to the right of the reference widget.
        ORIENTATION_CENTERED lays out the added widget and within the parent and all child centered.
        """
        if properties & ORIENTATION_ABSOLUTE != 0:
            return
        if properties & ORIENTATION_NO_BUFFER != 0:
            buffer = 0
        else:
            buffer = BUFFER
        if (properties & ORIENTATION_MODE_MASK) == ORIENTATION_RELATIVE:
            widget.translate(self.left, self.top)
            return
        elif last is None:  # orientation = origin
            widget.translate(self.left - widget.left, self.top - widget.top)
        elif (properties & ORIENTATION_GRID) != 0:
            dim = properties & ORIENTATION_DIM_MASK
            if (properties & ORIENTATION_VERTICAL) != 0:
                if dim == 0:  # Vertical
                    if self.height >= last.bottom - self.top + widget.height:
                        # add to line
                        widget.translate(
                            last.left - widget.left, last.bottom - widget.top
                        )
                    else:
                        # line return
                        widget.translate(
                            last.right - widget.left + buffer, self.top - widget.top
                        )
            else:
                if dim == 0:  # Horizontal
                    if self.width >= last.right - self.left + widget.width:
                        # add to line
                        widget.translate(
                            last.right - widget.left + buffer, last.top - widget.top
                        )
                    else:
                        # line return
                        widget.translate(
                            self.left - widget.left, last.bottom - widget.top + buffer
                        )
        elif (properties & ORIENTATION_HORIZONTAL) != 0:
            widget.translate(last.right - widget.left + buffer, last.top - widget.top)
        elif (properties & ORIENTATION_VERTICAL) != 0:
            widget.translate(last.left - widget.left, last.bottom - widget.top + buffer)
        if properties & ORIENTATION_CENTERED:
            self.center_children()

    def center_children(self):
        """
        Centers the children of the current widget within the current widget.
        """
        child_bounds = self.union_children_bounds()
        dx = self.left - (child_bounds[0] + child_bounds[2]) / 2.0
        dy = self.top - (child_bounds[1] + child_bounds[3]) / 2.0
        if dx != 0 and dy != 0:
            for w in self:
                w.translate_loop(dx, dy)

    def center_widget(self, x, y=None):
        """
        Moves the current widget to center within the bounds of the children.
        """
        if y is None:
            y = x.y
            x = x.x
        child_bounds = self.union_children_bounds()
        cx = (child_bounds[0] + child_bounds[2]) / 2.0
        cy = (child_bounds[1] + child_bounds[3]) / 2.0
        self.translate(x - cx, y - cy)

    def set_position(self, x, y=None):
        """
        Sets the absolute position of this widget by moving it from its current position
        to given position.
        """
        if y is None:
            y = x.y
            x = x.x
        dx = x - self.left
        dy = y - self.top
        self.translate(dx, dy)

    def remove_all_widgets(self):
        """
        Remove all widgets from the current widget.
        """
        for w in self:
            if w is None:
                continue
            w.parent = None
            w.notify_removed_from_parent(self)
            self.notify_removed_child(w)
        self.clear()
        try:
            self.scene.notify_tree_changed()
        except AttributeError:
            pass

    def remove_widget(self, widget=None):
        """
        Remove the given widget from being a child of the current widget.
        """
        if widget is None:
            return
        if isinstance(widget, Widget):
            self.remove(widget)
        elif isinstance(widget, int):
            index = widget
            widget = self[index]
            del self[index]
        widget.parent = None
        widget.notify_removed_from_parent(self)
        self.notify_removed_child(widget)
        try:
            self.scene.notify_tree_changed()
        except AttributeError:
            pass

    def set_widget(self, index, widget):
        """
        Sets the given widget at the index to replace the child currently at the position of that widget.
        """
        w = self[index]
        self[index] = widget
        widget.parent = self
        widget.notify_added_to_parent(self)
        self.notify_removed_child(w)
        try:
            self.scene.notify_tree_changed()
        except AttributeError:
            pass

    def on_matrix_change(self):
        """
        Notification of a changed matrix.
        """
        pass

    def scene_matrix_reset(self):
        """
        Resets the scene matrix.
        """
        self.matrix.reset()
        self.on_matrix_change()

    def scene_post_scale(self, sx, sy=None, ax=0, ay=0):
        """
        Adds a post_scale to the matrix.
        """
        self.matrix.post_scale(sx, sy, ax, ay)
        self.on_matrix_change()

    def scene_post_pan(self, px, py):
        """
        Adds a post_pan to the matrix.
        """
        self.matrix.post_translate(px, py)
        self.on_matrix_change()

    def scene_post_rotate(self, angle, rx=0, ry=0):
        """
        Adds a post_rotate to the matrix.
        """
        self.matrix.post_rotate(angle, rx, ry)
        self.on_matrix_change()

    def scene_pre_scale(self, sx, sy=None, ax=0, ay=0):
        """
        Adds a pre_scale to the matrix()
        """
        self.matrix.pre_scale(sx, sy, ax, ay)
        self.on_matrix_change()

    def scene_pre_pan(self, px, py):
        """
        Adds a pre_pan to the matrix()
        """
        self.matrix.pre_translate(px, py)
        self.on_matrix_change()

    def scene_pre_rotate(self, angle, rx=0, ry=0):
        """
        Adds a pre_rotate to the matrix()
        """
        self.matrix.pre_rotate(angle, rx, ry)
        self.on_matrix_change()

    def get_scale_x(self):
        """
        Gets the scale_x of the current matrix
        """
        return self.matrix.value_scale_x()

    def get_scale_y(self):
        """
        Gets the scale_y of the current matrix
        """
        return self.matrix.value_scale_y()

    def get_skew_x(self):
        """
        Gets the skew_x of the current matrix()
        """
        return self.matrix.value_skew_x()

    def get_skew_y(self):
        """
        Gets the skew_y of the current matrix()
        """
        return self.matrix.value_skew_y()

    def get_translate_x(self):
        """
        Gets the translate_x of the current matrix()
        """
        return self.matrix.value_trans_x()

    def get_translate_y(self):
        """
        Gets the translate_y of the current matrix()
        """
        return self.matrix.value_trans_y()

    def show(self, flag=None):
        """
        This does not automatically display the widget (yet)
        """
        if flag is None:
            flag = True
        self.visible = flag

    def hide(self, flag=None):
        """
        This does not automatically display the widget (yet)
        """
        if flag is None:
            flag = True
        self.visible = not flag
