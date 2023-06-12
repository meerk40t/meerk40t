from meerk40t.core.cutcode.cutobject import CutObject
from meerk40t.tools.rasterplotter import RasterPlotter


class RasterCut(CutObject):
    """
    Rastercut accepts an image of type "L" or "1", and an offset in the x and y.
    """

    def __init__(
        self,
        image,
        offset_x,
        offset_y,
        step_x,
        step_y,
        inverted=False,
        bidirectional=True,
        horizontal=True,
        start_on_top=True,
        start_on_left=True,
        overscan=0,
        settings=None,
        passes=1,
        parent=None,
        color=None,
    ):
        CutObject.__init__(
            self, settings=settings, passes=passes, parent=parent, color=color
        )
        assert image.mode in ("L", "1")
        self.first = True  # Raster cuts are always first within themselves.
        self.image = image
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.step_x = step_x
        self.step_y = step_y
        # if False -> burn in one direction, if True -> burn back and forth
        self.bidirectional = bidirectional
        self.horizontal = horizontal
        self.start_on_top = start_on_top
        self.start_on_left = start_on_left
        self.width, self.height = image.size
        self.inverted = inverted
        self.scan = overscan
        if inverted:
            skip_pixel = 255

            def image_filter(pixel):
                return pixel / 255.0

        else:
            skip_pixel = 0

            def image_filter(pixel):
                return (255 - pixel) / 255.0

        self.plot = RasterPlotter(
            data=image.load(),
            width=self.width,
            height=self.height,
            horizontal=self.horizontal,
            start_on_top=self.start_on_top,
            start_on_left=self.start_on_left,
            bidirectional=self.bidirectional,
            skip_pixel=skip_pixel,
            overscan=self.scan,
            offset_x=self.offset_x,
            offset_y=self.offset_y,
            step_x=self.step_x,
            step_y=self.step_y,
            filter=image_filter,
        )

    def reversible(self):
        return False

    def reverse(self):
        pass

    @property
    def start(self):
        return self.plot.initial_position_in_scene()

    @property
    def end(self):
        return self.plot.final_position_in_scene()

    def lower(self):
        return self.plot.offset_y + self.height

    def upper(self):
        return self.plot.offset_y

    def right(self):
        return self.plot.offset_x + self.width

    def left(self):
        return self.plot.offset_x

    def length(self):
        """
        crosshatch will be translated into two passes, so we have either a clear horizontal or a clear vertical

        self.scan_x * width in pixel = real width

        overscan is in device units

        @return:
        """

        if self.horizontal:
            scanlines = self.height
            scan_step = self.step_y
            scan_stride = self.step_x
            scan_distance = self.width * scan_stride
        else:
            scanlines = self.width
            scan_stride = self.step_x
            scan_step = self.step_y
            scan_distance = self.height * scan_stride
        # Total scan-distance is pixel_distance plus overscan
        scan_distance += self.scan
        if not self.bidirectional:
            # Burning in only one direction means we have 2 x distance
            scan_distance *= 2
        total_distance_per_scanline = scan_distance + scan_step
        return scanlines * total_distance_per_scanline

    def extra(self):
        return self.width * 1.4  # 105ms for the turnaround.

    def major_axis(self):
        return 0 if self.plot.horizontal else 1

    def x_dir(self):
        return 1 if self.plot.start_on_left else -1

    def y_dir(self):
        return 1 if self.plot.start_on_top else -1

    def generator(self):
        return self.plot.plot()
