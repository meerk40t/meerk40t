import os
from svgelements import *
from LaserNode import *
from EgvParser import parse_egv
from xml.etree.cElementTree import Element, ElementTree, SubElement


class SVGWriter:
    def __init__(self):
        self.project = None

    def initialize(self, project):
        self.project = project
        project.setting(int, "bed_width", 320)
        project.setting(int, "bed_height", 220)
        project.add_saver("SVGWriter", self)

    def save_types(self):
        yield "Scalable Vector Graphics", "svg", "image/svg+xml"

    def versions(self):
        yield 'default'

    def create_svg_dom(self):
        root = Element(SVG_NAME_TAG)
        root.set(SVG_ATTR_VERSION, SVG_VALUE_VERSION)
        root.set(SVG_ATTR_XMLNS, SVG_VALUE_XMLNS)
        root.set(SVG_ATTR_XMLNS_LINK, SVG_VALUE_XLINK)
        root.set(SVG_ATTR_XMLNS_EV, SVG_VALUE_XMLNS_EV)
        root.set(SVG_ATTR_WIDTH, '%fmm' % self.project.bed_width)
        root.set(SVG_ATTR_HEIGHT, '%fmm' % self.project.bed_height)
        mils_per_mm = 39.3701
        mil_width = self.project.bed_width * mils_per_mm
        mil_height = self.project.bed_height * mils_per_mm
        viewbox = '%d %d %d %d' % (0, 0, round(mil_width), round(mil_height))
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = self.project.elements
        for node in elements.flat_elements(types=('image', 'path', 'text'), passes=False):
            element = node.element
            if node.type == 'path':
                path = SubElement(root, SVG_TAG_PATH)
                path.set(SVG_ATTR_DATA, element.d())
                path.set(SVG_ATTR_STROKE, str(element.stroke))
                path.set(SVG_ATTR_FILL, str(element.fill))
            elif node.type == 'text':
                text = SubElement(root, SVG_TAG_TEXT)
                text.set(SVG_ATTR_STROKE, str(element.stroke))
                text.set(SVG_ATTR_FILL, str(element.fill))
            else:  #  image
                image = SubElement(root, SVG_TAG_IMAGE)
                image.set(SVG_ATTR_STROKE, str(element.stroke))
                image.set(SVG_ATTR_FILL, str(element.fill))
        return ElementTree(root)

    def save(self, f, version='default'):
        tree = self.create_svg_dom()
        tree.write(f)


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
