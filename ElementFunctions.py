from LaserOperation import RasterOperation
from svgelements import *


class ElementFunctions:

    @staticmethod
    def needs_actualization(operation, image_element):
        if not isinstance(image_element, SVGImage):
            return False
        if not isinstance(operation, RasterOperation):
            return False
        op_step = operation.raster_step
        if 'raster_step' in image_element.values:
            img_step = float(image_element.values['raster_step'])
        else:
            img_step = 1.0
        if op_step != img_step:
            return True  # Different step values force require actualization.

        m = image_element.transform
        # Transformation must be uniform to permit native rastering.
        return m.a != img_step or m.b != 0.0 or m.c != 0.0 or m.d != img_step


    @staticmethod
    def make_actual(image):
        """
        Makes PIL image actual in that it manipulates the pixels to actually exist
        rather than simply apply the transform on the image to give the resulting image.
        Since our goal is to raster the images real pixels this is required.

        SVG matrices are defined as follows.
        [a c e]
        [b d f]

        Pil requires a, c, e, b, d, f accordingly.
        """
        if not isinstance(image, SVGImage):
            return
        from PIL import Image

        pil_image = image.image
        image.cache = None
        m = image.transform
        if 'raster_step' in image.values:
            step = float(image.values['raster_step'])
        else:
            step = 1.0

        image.transform.pre_scale(1.0 / step, 1.0 / step)
        tx = m.value_trans_x()
        ty = m.value_trans_y()
        m.e = 0.0
        m.f = 0.0
        image.transform.pre_scale(1.0 / step, 1.0 / step)
        bbox = ElementFunctions.bounding_box(image)
        width = int(ceil(bbox[2] - bbox[0]))
        height = int(ceil(bbox[3] - bbox[1]))
        m.inverse()
        pil_image = pil_image.transform((width, height), Image.AFFINE,
                                        (m.a, m.c, m.e, m.b, m.d, m.f),
                                        resample=Image.BICUBIC)
        image.transform.reset()
        image.transform.post_scale(step, step)
        image.transform.post_translate(tx, ty)
        image.image = pil_image
        pil_image.image_width = width
        pil_image.image_height = height

    @staticmethod
    def reify_matrix(self):
        """Apply the matrix to the path and reset matrix."""
        self.element = abs(self.element)
        self.scene_bounds = None

    @staticmethod
    def set_native(element):
        tx = element.transform.value_trans_x()
        ty = element.transform.value_trans_y()
        step = float(element.raster_step)

        element.transform.reset()
        element.transform.post_scale(step, step)
        element.transform.post_translate(tx, ty)
        step = float(element.raster_step)
        element.transform.pre_scale(step, step)

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

