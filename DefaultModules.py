import os
from svgelements import *
from LaserNode import *
from EgvParser import parse_egv


class SVGLoader:
    def __init__(self):
        self.project = None

    def initialize(self, project):
        self.project = project
        project.setting(int, "bed_width", 320)
        project.setting(int, "bed_height", 220)
        project.add_loader("SVGLoader", self)

    def load_types(self):
        yield "Scalable Vector Graphics", ("svg",), "image/svg+xml"

    def load(self, pathname, group=None):
        scale_factor = 1000.0 / 96.0
        svg = SVG(pathname).elements(width='%fmm' % (self.project.bed_width),
                                     height='%fmm' % (self.project.bed_height),
                                     ppi=96.0,
                                     transform='scale(%f)' % scale_factor)
        context = self.project.elements

        if group is None:
            group = LaserNode()
            group['filepath'] = pathname
            group.name = os.path.basename(pathname)
            context.append(group)

        context = group
        append_list = []
        for element in svg:
            if isinstance(element, SVGText):
                pe = LaserNode(element)
                append_list.append(pe)
            elif isinstance(element, Path):
                pe = LaserNode(element)
                append_list.append(pe)
            elif isinstance(element, Shape):
                e = Path(element)
                e.reify()  # In some cases the shape could not have reified, the path must.
                pe = LaserNode(e)
                append_list.append(pe)
            elif isinstance(element, SVGImage):
                try:
                    element.load(os.path.dirname(pathname))
                    if element.image is not None:
                        pe = LaserNode(element)
                        append_list.append(pe)
                except OSError:
                    pass
        context.append_all(append_list)


class EgvLoader:
    def __init__(self):
        self.project = None

    def initialize(self, project):
        self.project = project
        project.add_loader("EGVLoader", self)

    def load_types(self):
        yield "Engrave Files", ("egv",), "application/x-egv"

    def load(self, pathname, group):
        context = self.project.elements
        if group is None:
            group = LaserNode()
            group['filepath'] = pathname
            group.name = os.path.basename(pathname)
            context.append(group)
        context = group
        for event in parse_egv(pathname):
            path = event['path']
            if len(path) > 0:
                element = LaserNode(path)
                context.append(element)
                if 'speed' in event:
                    element['speed'] = event['speed']
            if 'raster' in event:
                raster = event['raster']
                image = raster.get_image()
                if image is not None:
                    element = LaserNode(image)
                    context.append(element)
                    if 'speed' in event:
                        element['speed'] = event['speed']


class ImageLoader:
    def __init__(self):
        self.project = None

    def initialize(self, project):
        self.project = project
        project.add_loader("ImageLoader", self)

    def load_types(self):
        yield "Portable Network Graphics", ("png",), "image/png"
        yield "Bitmap Graphics", ("bmp",), "image/bmp"
        yield "EPS Format", ("eps",), "image/eps"
        yield "GIF Format", ("gif",), "image/gif"
        yield "Icon Format", ("ico",), "image/ico"
        yield "JPEG Format", ("jpg", "jpeg", "jpe"), "image/jpeg"
        yield "Webp Format", ("webp",), "image/webp"

    def load(self, pathname, group=None):
        context = self.project.elements
        image = SVGImage({'href': pathname, 'width': "100%", 'height': "100%"})
        image.load()
        element = LaserNode(image)
        if group is None:
            group = LaserNode()
            group.element.values.update(element.element.values)
            group['filepath'] = pathname
            group.name = os.path.basename(pathname)
            context.append(group)
        context = group
        context.append(element)
