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

    def set_geometry(self, geom):
        # We have been given a new geometry.
        # If we have a "geometry" property then we need to set it
        # This method needs to be overridden in subclasses
        # if a special handling is required, eg. node type change.
        if hasattr(self, "geometry"):
            self.geometry = geom
            self.altered()
        return self


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


class OperationMixin:
    """
    Mixin class providing common functionality for operation nodes.

    This mixin should be inherited by operation node classes (CutOpNode, EngraveOpNode,
    RasterOpNode, ImageOpNode, DotsOpNode, etc.) that need element classification and
    color attribute management capabilities.

    Operation nodes that inherit this mixin should:
    - Implement would_classify() for classification decision logic
    - Define self.allowed_attributes list for color attribute management
    - Define self._allowed_elements_dnd tuple for drag-and-drop validation

    This keeps operation-specific patterns out of the base Node class which is used by
    all node types, not just operations.
    """

    def classify(self, node, fuzzy=False, fuzzydistance=100, usedefault=False):
        """
        Classify a node and add it as a reference if it matches operation criteria.

        This method provides a standard pattern: it calls would_classify() to make
        the classification decision, and if successful, adds a reference to the node.

        Subclasses should implement would_classify() with their classification logic
        rather than overriding this method. The would_classify() method should return
        a tuple of (classified: bool, should_break: bool, feedback: list or None).

        @param node: The node to classify
        @param fuzzy: Whether to use fuzzy color matching
        @param fuzzydistance: Distance threshold for fuzzy matching
        @param usedefault: Whether to use default classification
        @return: Tuple of (classified: bool, should_break: bool, feedback: list or None)
        """
        if not hasattr(self, "would_classify"):
            # Fallback for classes that don't implement would_classify yet
            return False, False, None

        classified, should_break, feedback = self.would_classify(
            node,
            fuzzy=fuzzy,
            fuzzydistance=fuzzydistance,
            usedefault=usedefault,
        )
        if classified:
            self.add_reference(node)
        return classified, should_break, feedback

    def is_referenced(self, node):
        """
        Check if a node is already referenced as a child of this operation.

        @param node: The node to check
        @return: True if the node is already referenced, False otherwise
        """
        for e in self.children:
            if e is node:
                return True
            if hasattr(e, "node") and e.node is node:
                return True
        return False

    def valid_node_for_reference(self, node):
        """
        Check if a node type is valid for this operation.

        Default implementation checks against self._allowed_elements_dnd.
        Subclasses can override for custom validation logic.

        @param node: The node to validate
        @return: True if the node can be added to this operation, False otherwise
        """
        if hasattr(self, "_allowed_elements_dnd"):
            return node.type in self._allowed_elements_dnd
        return False

    def has_color_attribute(self, attribute):
        """
        Check if a color attribute is enabled for classification.

        @param attribute: The attribute name (e.g., "stroke", "fill")
        @return: True if the attribute is in allowed_attributes, False otherwise
        """
        return attribute in self.allowed_attributes

    def add_color_attribute(self, attribute):
        """
        Add a color attribute to the list of attributes used for classification.

        @param attribute: The attribute name to add (e.g., "stroke", "fill")
        """
        if attribute not in self.allowed_attributes:
            self.allowed_attributes.append(attribute)

    def remove_color_attribute(self, attribute):
        """
        Remove a color attribute from the list used for classification.

        @param attribute: The attribute name to remove
        """
        if attribute in self.allowed_attributes:
            self.allowed_attributes.remove(attribute)

    def has_attributes(self):
        """
        Check if any color attributes are configured for classification.

        @return: True if stroke or fill attributes are enabled, False otherwise
        """
        return "stroke" in self.allowed_attributes or "fill" in self.allowed_attributes
