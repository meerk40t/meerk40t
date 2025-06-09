"""
Mixins for nodes are aspects of code which can and should be used between multiple different nodes which convey some
basic functionality.

The use of ABC allows @abstractmethod decorators which require any subclass to implement the required method.
"""

from abc import ABC
from math import sqrt


class Stroked(ABC):
    """
    Stroked nodes provide a stroke_scaled matrix controlled stroke mixin. Such that the stroke scaling can be enabled
    and disabled, and it will increase or decrease the implied_stroke_width. If stroke scaling is disabled then the
    stroke_width is independent to the scaling of the node (dictated by the .matrix attribute).
    """

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._acts_as_keyhole = False

    @property
    def stroke_scaled(self):
        return self.stroke_scale

    @stroke_scaled.setter
    def stroke_scaled(self, v):
        """
        Setting stroke_scale directly will not resize the stroke-width based on current scaling. This function allows
        the toggling of the stroke-scaling without the current stroke_width being affected.

        @param v:
        @return:
        """
        if bool(v) == bool(self.stroke_scale):
            # Unchanged.
            return
        if not v:
            self.stroke_width *= self.stroke_factor
        self.stroke_width_zero()
        self.stroke_scale = v

    @property
    def implied_stroke_width(self):
        """
        The implied stroke width is stroke_width if not scaled or the scaled stroke_width if scaled.

        @return:
        """
        if self.stroke_scale:
            factor = self.stroke_factor
        else:
            factor = 1
        if hasattr(self, "stroke"):
            # print (f"Have stroke {self.stroke}, {type(self.stroke).__name__}")
            if self.stroke is None or self.stroke.argb is None:
                # print ("set to zero")
                factor = 0

        return self.stroke_width * factor

    @property
    def stroke_factor(self):
        """
        The stroke factor is the ratio of the new to old stroke-width scale.

        @return:
        """
        matrix = self.matrix
        stroke_one = sqrt(abs(matrix.determinant))
        try:
            return stroke_one / self._stroke_zero
        except (AttributeError, ZeroDivisionError, TypeError):
            return 1.0

    def stroke_reify(self):
        """Set the stroke width to the real stroke width."""
        if self.stroke_scale:
            self.stroke_width *= self.stroke_factor
        self.stroke_width_zero()

    def stroke_width_zero(self):
        """
        Ensures the current stroke scale is marked as stroke_zero.
        @return:
        """
        matrix = self.matrix
        self._stroke_zero = sqrt(abs(matrix.determinant))


class FunctionalParameter(ABC):
    """
    Functional Parameters mixin allows the use and utility of functional parameters for this node type.
    """

    def __init__(self, *args, **kwargs):
        self.mkparam = None
        super().__init__()

    @property
    def functional_parameter(self):
        return self.mkparam

    @functional_parameter.setter
    def functional_parameter(self, value):
        if isinstance(value, (list, tuple)):
            self.mkparam = value


class LabelDisplay(ABC):
    """
    Any node inheriting this allow the display of the label on the scene
    """

    def __init__(self, *args, **kwargs):
        self.label_display = False
        super().__init__()


class Suppressable(ABC):
    """
    Any node inheriting this can be suppressed
    """

    def __init__(self, *args, **kwargs):
        self.hidden = False
        if "hidden" in kwargs:
            if isinstance(kwargs["hidden"], str):
                if kwargs["hidden"].lower() == "true":
                    kwargs["hidden"] = True
                else:
                    kwargs["hidden"] = False
            self.hidden = kwargs["hidden"]
        super().__init__()
