from meerk40t.core.node.elem_default import ElemNode


class ImageNode(ElemNode):
    """
    ImageNode is the bootstrapped node type for the 'elem image' type.
    """

    def __init__(
        self,
        data_object,
        image=None,
        matrix=None,
        overscan=None,
        direction=None,
        dpi=500,
        step_x=None,
        step_y=None,
        **kwargs,
    ):
        super(ImageNode, self).__init__(data_object, matrix=matrix)
        self.image = image
        self.overscan = overscan
        self.direction = direction
        self.dpi = dpi
        self.step_x = step_x
        self.step_y = step_y

    def __copy__(self):
        return ImageNode(
            image=self.image,
            matrix=self.matrix,
            overscan=self.overscan,
            direction=self.direction,
            dpi=self.dpi,
            step_x=self.step_x,
            step_y=self.step_y,
        )

    @property
    def bounds(self):
        if self._bounds_dirty:
            self._calculate_bounds()
        return self._bounds

    def default_map(self, default_map=None):
        default_map = super(ImageNode, self).default_map(default_map=default_map)
        if self.object is not None:
            default_map.update(self.object.values)
        if "stroke" not in default_map:
            default_map["stroke"] = "None"
        if "fill" not in default_map:
            default_map["fill"] = "None"
        if "stroke-width" not in default_map:
            default_map["stroke-width"] = "None"
        if "dpi" not in default_map:
            default_map["dpi"] = self.dpi
        return default_map
