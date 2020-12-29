from copy import copy

from svgelements import SVGImage

"""
This file class/collection is part of an exploration of the modification scheme.

This highlights problems and requirements for lazy modifications of elements.
"""


class Modification(list):
    """
    Modifications are intended to be lazy implemented changes to SVGElement objects and groups. The intent is to
    provide a method for delayed modifications of data. In a modification tree.

    Modifications are functions called on other Modifications. With end-nodes that wrap the core work types.
    Type Input is the input type kind of element this is intended to act upon.
    Type Output is the output type of the element this is intended to produce.

    External modifications are performed by programs usually with command line accesses. These may fail.

    Established datatypes are:
    element, shape, path, rect, circle, polyline, polygon, image, blob_ruida, blob_gcode, blob_lhymicro

    The output type of a modification counts as that type of object, in a lazy fashion. If the object is required,
    then .get() should be called. This will create a cached object, by applying the modification and producing the
    promised object.
    """

    def __init__(self, input_types, output_type):
        list.__init__(self)
        self.input_types = input_types
        self.output_type = output_type
        self.object = None

    def provides(self, name_type):
        return self.output_type == name_type

    def get(self):
        raise NotImplementedError


class Wrap(Modification):
    """
    Wraps a simple copy of an output type. When get() is called produces a copy.
    """
    def __init__(self, obj, output_type):
        Modification.__init__('none', output_type)
        self.object = obj

    def get(self):
        return copy(self.object)


class DitherImage(Modification):
    """
    Example image -> image modification.

    If image to image then each image makes 1 image. Needs to either limit the size.
    Or process groups of images.

    This duplicates code already working in Console. But, the console use is more specific
    and less adaptive.

    """
    def __init__(self):
        Modification.__init__('image', 'image')

    def get(self):
        elems = [e.get() for e in self if e.provides('image')]
        for element in elems:
            img = element.image
            if img.mode == 'RGBA':
                pixel_data = img.load()
                width, height = img.size
                for y in range(height):
                    for x in range(width):
                        if pixel_data[x, y][3] == 0:
                            pixel_data[x, y] = (255, 255, 255, 255)
            element.image = img.convert("1")


class MakeImage(Modification):
    """
    Make image requires LaserRender and thus wx as a whole and would prevent CLI versions of MeerK40t
    from fully processing this type of output. Also, it has a specific tweak that negates all the work
    done on the objects since an increase of the step would change the the order of operations
    and since we use the initial copy, all values on that work chain are negated.
    """
    def __init__(self):
        Modification.__init__('element', 'image')
        self.step = 1

    def set_step(self, step):
        self.object = None
        self.step = step

    def get(self):
        pass
        # from LaserRender import LaserRender
        #
        # elems = [e.get() for e in self if e.provides('element')]
        #
        # from OperationPreprocessor import OperationPreprocessor
        # bounds = OperationPreprocessor.bounding_box(elems)
        # if bounds is None:
        #     return None
        # xmin, ymin, xmax, ymax = bounds
        #
        # renderer = LaserRender(self.context)
        # image = renderer.make_raster(self, bounds, step=self.step)
        # image_element = SVGImage(image=image)
        # image_element.transform.post_translate(xmin, ymin)
        # self.object = image_element
        # return self.object




