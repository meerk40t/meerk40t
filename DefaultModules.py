import os
from io import BytesIO

from base64 import b64encode

from K40Controller import K40Controller
from Kernel import Spooler, Module, Backend, Device
from LaserCommandConstants import COMMAND_RESET
from LhymicroInterpreter import LhymicroInterpreter
from LaserNode import *
from EgvParser import parse_egv
from xml.etree.cElementTree import Element, ElementTree, SubElement


class K40StockDevice(Device):
    def __init__(self, uid=None):
        Device.__init__(self)
        self.uid = uid

    def __repr__(self):
        return "K40StockDevice(uid='%s')" % str(self.uid)

    def initialize(self, kernel, name=''):
        self.kernel = kernel
        self.uid = name
        self.setting(int, 'usb_index', -1)
        self.setting(int, 'usb_bus', -1)
        self.setting(int, 'usb_address', -1)
        self.setting(int, 'usb_serial', -1)
        self.setting(int, 'usb_version', -1)

        self.setting(bool, 'mock', False)
        self.setting(int, 'packet_count', 0)
        self.setting(int, 'rejected_count', 0)
        self.setting(int, "buffer_max", 900)
        self.setting(bool, "buffer_limit", True)
        self.setting(bool, "autolock", True)
        self.setting(bool, "autohome", False)
        self.setting(bool, "autobeep", True)
        self.setting(bool, "autostart", True)

        self.setting(str, "board", 'M2')
        self.setting(bool, "rotary", False)
        self.setting(float, "scale_x", 1.0)
        self.setting(float, "scale_y", 1.0)
        self.setting(int, "_stepping_force", None)
        self.setting(float, "_acceleration_breaks", float("inf"))
        self.setting(int, "bed_width", 320)
        self.setting(int, "bed_height", 220)

        self.signal("bed_size", (self.bed_width, self.bed_height))

        self.add_control("Emergency Stop", self.emergency_stop)
        self.add_control("Debug Device", self._start_debugging)

        kernel.add_device(name, self)
        self.open()

    def emergency_stop(self):
        self.spooler.realtime(COMMAND_RESET, 1)

    def open(self):
        self.pipe = K40Controller(self)
        self.interpreter = LhymicroInterpreter(self)
        self.spooler = Spooler(self)
        self.hold_condition = lambda v: self.buffer_limit and len(self.pipe) > self.buffer_max

    def close(self):
        self.spooler.clear_queue()
        self.emergency_stop()
        self.pipe.close()


class K40StockBackend(Module, Backend):
    def __init__(self):
        Module.__init__(self)
        Backend.__init__(self, uid='K40Stock')
        self.autolock = True
        self.mock = True

    def initialize(self, kernel, name='K40Stock'):
        self.kernel = kernel
        self.kernel.add_backend(name, self)
        self.kernel.setting(str, 'device_list', '')
        self.kernel.setting(str, 'device_primary', '')
        for device in kernel.device_list.split(';'):
            self.create_device(device)
            if device == kernel.device_primary:
                self.kernel.activate_device(device)

    def create_device(self, uid):
        device = K40StockDevice()
        device.initialize(self.kernel, uid)


class SVGWriter:
    def __init__(self):
        self.kernel = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        kernel.add_saver("SVGWriter", self)

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
        root.set("xmlns:meerK40t", "https://github.com/meerk40t/meerk40t/wiki/Namespace")
        # Native unit is mils, these must convert to mm and to px
        mils_per_mm = 39.3701
        mils_per_px = 1000.0 / 96.0
        px_per_mils = 96.0 / 1000.0
        if self.kernel.device is None:
            self.kernel.setting(int, "bed_width", 320)
            self.kernel.setting(int, "bed_height", 220)
            mm_width = self.kernel.bed_width
            mm_height = self.kernel.bed_height
        else:
            self.kernel.device.setting(int, "bed_width", 320)
            self.kernel.device.setting(int, "bed_height", 220)
            mm_width = self.kernel.device.bed_width
            mm_height = self.kernel.device.bed_height
        root.set(SVG_ATTR_WIDTH, '%fmm' % mm_width)
        root.set(SVG_ATTR_HEIGHT, '%fmm' % mm_height)
        px_width = mm_width * mils_per_mm * px_per_mils
        px_height = mm_height * mils_per_mm * px_per_mils

        viewbox = '%d %d %d %d' % (0, 0, round(px_width), round(px_height))
        scale = 'scale(%f)' % px_per_mils
        root.set(SVG_ATTR_VIEWBOX, viewbox)
        elements = self.kernel.elements
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

    def initialize(self, project, name=None):
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
        return context


class EgvLoader:
    def __init__(self):
        self.project = None

    def initialize(self, project, name=None):
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
        return context


class ImageLoader:
    def __init__(self):
        self.project = None

    def initialize(self, project, name=None):
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
        return context
