from svgelements import *


class ElementFunctions:

    @staticmethod
    def needs_actualization(image):
        if not isinstance(image, SVGImage):
            return False
        m = image.transform
        if 'raster_step' in image.values: # todo: This should draw values parent operation it has no connection to.
            s = float(image.values['raster_step'])
        else:
            s = 1.0
        return m.a != s or m.b != 0.0 or m.c != 0.0 or m.d != s

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

        tx = m.value_trans_x()
        ty = m.value_trans_y()
        m.e = 0.0
        m.f = 0.0
        image.transform.pre_scale(1.0 / step, 1.0 / step)
        bbox = image.bbox()
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
    def set_native(self):
        tx = self.transform.value_trans_x()
        ty = self.transform.value_trans_y()
        step = float(self.raster_step)

        self.transform.reset()
        self.transform.post_scale(step, step)
        self.transform.post_translate(tx, ty)
        step = float(self.raster_step)
        self.transform.pre_scale(step, step)

