
from svgelements import *
from LaserCommandConstants import *
from LaserOperation import LaserOperation, RasterOperation
from LaserRender import LaserRender


class OperationPreprocessor:

    def __init__(self):
        self.device = None
        self.commands = []
        self.operations = None

    def process(self, operations):
        self.operations = operations
        if self.device.rotary:
            self.conditional_jobadd_scale_rotary()
        self.conditional_jobadd_actualize_image()
        self.conditional_jobadd_make_raster()

    def execute(self):
        # Using copy of commands, so commands can add ops.
        commands = self.commands[:]
        self.commands = []
        for cmd in commands:
            cmd()

    def conditional_jobadd_make_raster(self):
        for op in self.operations:
            if isinstance(op, RasterOperation):
                if len(op) == 0:
                    continue
                if len(op) == 1 and isinstance(op[0], SVGImage):
                    continue  # make raster not needed since its a single real raster.
                self.jobadd_make_raster()
                return True
        return False

    def jobadd_make_raster(self):
        def make_image():
            for op in self.operations:
                if isinstance(op, RasterOperation):
                    if len(op) == 1 and isinstance(op[0], SVGImage):
                        continue
                    renderer = LaserRender(self.device.device_root)
                    bounds = OperationPreprocessor.bounding_box(op)
                    if bounds is None:
                        return None
                    xmin, ymin, xmax, ymax = bounds

                    image = renderer.make_raster(op, bounds, step=op.raster_step)
                    image_element = SVGImage(image=image)
                    image_element.transform.post_translate(xmin, ymin)
                    op.clear()
                    op.append(image_element)

        self.commands.append(make_image)

    def conditional_jobadd_actualize_image(self):
        for op in self.operations:
            if isinstance(op, RasterOperation):
                for elem in op:
                    if OperationPreprocessor.needs_actualization(elem, op.raster_step):
                        self.jobadd_actualize_image()
                        return

    def jobadd_actualize_image(self):
        def actualize():
            for op in self.operations:
                if isinstance(op, RasterOperation):
                    for elem in op:
                        if OperationPreprocessor.needs_actualization(elem, op.raster_step):
                            OperationPreprocessor.make_actual(elem, op.raster_step)
        self.commands.append(actualize)

    def conditional_jobadd_scale_rotary(self):
        if self.device.scale_x != 1.0 or self.device.scale_y != 1.0:
            self.jobadd_scale_rotary()

    def jobadd_scale_rotary(self):
        def scale_for_rotary():
            p = self.device
            scale_str = 'scale(%f,%f,%f,%f)' % (p.scale_x, p.scale_y, p.current_x, p.current_y)
            for o in self.operations:
                if isinstance(o, LaserOperation):
                    for e in o:
                        try:
                            e *= scale_str
                        except AttributeError:
                            pass
            self.conditional_jobadd_actualize_image()

        self.commands.append(scale_for_rotary)

    @staticmethod
    def home():
        yield COMMAND_WAIT_FINISH
        yield COMMAND_HOME

    @staticmethod
    def wait():
        wait_amount = 5.0
        yield COMMAND_WAIT_FINISH
        yield COMMAND_WAIT, wait_amount

    @staticmethod
    def beep():
        yield COMMAND_WAIT_FINISH
        yield COMMAND_BEEP

    @staticmethod
    def needs_actualization(image_element, step_level=None):
        if not isinstance(image_element, SVGImage):
            return False
        if step_level is None:
            if 'raster_step' in image_element.values:
                step_level = float(image_element.values['raster_step'])
            else:
                step_level = 1.0
        m = image_element.transform
        # Transformation must be uniform to permit native rastering.
        return m.a != step_level or m.b != 0.0 or m.c != 0.0 or m.d != step_level

    @staticmethod
    def make_actual(image_element, step_level=None):
        """
        Makes PIL image actual in that it manipulates the pixels to actually exist
        rather than simply apply the transform on the image to give the resulting image.
        Since our goal is to raster the images real pixels this is required.

        SVG matrices are defined as follows.
        [a c e]
        [b d f]

        Pil requires a, c, e, b, d, f accordingly.
        """
        if not isinstance(image_element, SVGImage):
            return
        from PIL import Image

        pil_image = image_element.image
        image_element.cache = None
        m = image_element.transform
        bbox = OperationPreprocessor.bounding_box([image_element])
        tx = bbox[0]
        ty = bbox[1]
        m.post_translate(-tx, -ty)
        element_width = int(ceil(bbox[2] - bbox[0]))
        element_height = int(ceil(bbox[3] - bbox[1]))
        if step_level is None:
            # If we are not told the step amount either draw it from the object or set it to default.
            if 'raster_step' in image_element.values:
                step_level = float(image_element.values['raster_step'])
            else:
                step_level = 1.0
        step_scale = 1 / step_level
        m.pre_scale(step_scale, step_scale)
        # step level requires the actual image be scaled down.
        m.inverse()

        if (m.value_skew_y() != 0.0 or m.value_skew_y() != 0.0) and pil_image.mode != 'RGBA':
            # If we are rotating an image without alpha, we need to convert it, or the rotation invents black pixels.
            pil_image = pil_image.convert('RGBA')

        pil_image = pil_image.transform((element_width, element_height), Image.AFFINE,
                                        (m.a, m.c, m.e, m.b, m.d, m.f),
                                        resample=Image.BICUBIC)
        image_element.image_width, image_element.image_height = (element_width, element_height)
        m.reset()

        box = pil_image.getbbox()
        width = box[2] - box[0]
        height = box[3] - box[1]
        if width != element_width and height != element_height:
            image_element.image_width, image_element.image_height = (width, height)
            pil_image = pil_image.crop(box)
            m.post_translate(box[0], box[1])
        # step level requires the new actualized matrix be scaled up.
        m.post_scale(step_level, step_level)
        m.post_translate(tx, ty)
        image_element.image = pil_image

    @staticmethod
    def reify_matrix(self):
        """Apply the matrix to the path and reset matrix."""
        self.element = abs(self.element)
        self.scene_bounds = None

    @staticmethod
    def bounding_box(elements):
        if isinstance(elements, SVGElement):
            elements = [elements]
        elif isinstance(elements, list):
            try:
                elements = [e.object for e in elements if isinstance(e.object, SVGElement)]
            except AttributeError:
                pass
        boundary_points = []
        for e in elements:
            box = e.bbox(False)
            if box is None:
                continue
            top_left = e.transform.point_in_matrix_space([box[0], box[1]])
            top_right = e.transform.point_in_matrix_space([box[2], box[1]])
            bottom_left = e.transform.point_in_matrix_space([box[0], box[3]])
            bottom_right = e.transform.point_in_matrix_space([box[2], box[3]])
            boundary_points.append(top_left)
            boundary_points.append(top_right)
            boundary_points.append(bottom_left)
            boundary_points.append(bottom_right)
        if len(boundary_points) == 0:
            return None
        xmin = min([e[0] for e in boundary_points])
        ymin = min([e[1] for e in boundary_points])
        xmax = max([e[0] for e in boundary_points])
        ymax = max([e[1] for e in boundary_points])
        return xmin, ymin, xmax, ymax

