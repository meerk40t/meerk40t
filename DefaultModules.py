import os
from io import BytesIO

from base64 import b64encode
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
        # Native unit is mils, these must convert to mm and to px
        mils_per_mm = 39.3701
        mils_per_px = 1000.0 / 96.0
        px_per_mils = 96.0 / 1000.0
        mm_width = self.project.bed_width
        mm_height = self.project.bed_height
        root.set(SVG_ATTR_WIDTH, '%fmm' % mm_width)
        root.set(SVG_ATTR_HEIGHT, '%fmm' % mm_height)
        px_width = mm_width * mils_per_mm * px_per_mils
        px_height = mm_height * mils_per_mm * px_per_mils

        viewbox = '%d %d %d %d' % (0, 0, round(px_width), round(px_height))
        scale = 'scale(%f)' % px_per_mils
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = self.project.elements
        for node in elements.flat_elements(types=('image', 'path', 'text'), passes=False):
            element = node.element
            if node.type == 'path':
                subelement = SubElement(root, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d())
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                for key, val in element.values.items():
                    if key in ('stroke-width', 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio'):
                        subelement.set(key, str(val))
            elif node.type == 'text':
                subelement = SubElement(root, SVG_TAG_TEXT)
                subelement.text = element.text
                t = Matrix(element.transform)
                t *= scale
                subelement.set('transform', 'matrix(%f, %f, %f, %f, %f, %f)' % (t.a, t.b, t.c, t.d, t.e, t.f))
                for key, val in element.values.items():
                    if key in ('stroke-width', 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio',
                               'font-family', 'font-size', 'font-weight'):
                        subelement.set(key, str(val))
            else: # Image.
                subelement = SubElement(root, SVG_TAG_IMAGE)
                stream = BytesIO()
                element.image.save(stream, format='PNG')
                png = b64encode(stream.getvalue()).decode('utf8')
                subelement.set('xlink:href', "data:image/png;base64,%s" % (png))
                subelement.set(SVG_ATTR_X, '0')
                subelement.set(SVG_ATTR_Y, '0')
                subelement.set(SVG_ATTR_WIDTH, str(element.image.width))
                subelement.set(SVG_ATTR_HEIGHT, str(element.image.height))
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                t = Matrix(element.transform)
                t *= scale
                subelement.set('transform', 'matrix(%f, %f, %f, %f, %f, %f)' % (t.a, t.b, t.c, t.d, t.e, t.f))
                for key, val in element.values.items():
                    if key in ('stroke-width', 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio'):
                        subelement.set(key, str(val))
            stroke = str(element.stroke)
            fill = str(element.fill)
            if stroke == 'None':
                stroke = SVG_VALUE_NONE
            if fill == 'None':
                fill = SVG_VALUE_NONE
            subelement.set(SVG_ATTR_STROKE, stroke)
            subelement.set(SVG_ATTR_FILL, fill)
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
