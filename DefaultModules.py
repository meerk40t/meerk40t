import os
from base64 import b64encode
from io import BytesIO
from xml.etree.cElementTree import Element, ElementTree, SubElement

from EgvParser import parse_egv
from K40Controller import K40Controller
from Kernel import Spooler, Module, Backend, Device
from LaserCommandConstants import *
from LhymicroInterpreter import LhymicroInterpreter
from svgelements import *

MILS_PER_MM = 39.3701


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
        self.setting(bool, 'quit', False)
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

    def shutdown(self, kernel):
        self.kernel.remove_backend(self.uid)
        self.kernel.remove_module(self.uid)

    def create_device(self, uid):
        device = K40StockDevice()
        device.initialize(self.kernel, uid)


class GRBLEmulator(Module):

    def __init__(self):
        Module.__init__(self)
        # Pipe.__init__(self)
        self.flip_x = 1  # Assumes the GCode is flip_x, -1 is flip, 1 is normal
        self.flip_y = 1  # Assumes the Gcode is flip_y,  -1 is flip, 1 is normal
        self.scale = MILS_PER_MM  # Initially assume mm mode 39.4 mils in an mm. G20 DEFAULT
        self.feed_scale = (self.scale / MILS_PER_MM) * (1.0 / 60.0)  # G94 DEFAULT, mm mode
        self.move_mode = 0
        self.on_mode = 1
        self.read_info = b"Grbl 1.1e ['$' for help]\r\n"

        self.comment = None
        self.code = ""
        self.value = ""
        self.command_map = {}

    def close(self):
        pass

    def open(self):
        pass

    def initialize(self, kernel, name=None):
        Module.initialize(kernel, name)
        self.kernel = kernel
        self.name = name

    def shutdown(self, kernel):
        Module.shutdown(self, kernel)

    def realtime_write(self, bytes_to_write):
        interpreter = self.kernel.device.interpreter
        if bytes_to_write == '?':  # Status report
            if interpreter.state == 0:
                state = 'Idle'
            else:
                state = 'Busy'
            x = self.kernel.device.current_x / self.scale
            y = self.kernel.device.current_y / self.scale
            z = 0.0
            parts = list()
            parts.append(state)
            parts.append('MPos:%f,%f,%f' % (x, y, z))
            f = self.kernel.device.interpreter.speed / self.feed_scale
            s = self.kernel.device.interpreter.power
            parts.append('FS:%f,%d' % (f, s))
            self.read_info = "<%s>\r\n" % '|'.join(parts)
        elif bytes_to_write == '~':  # Resume.
            interpreter.realtime_command(COMMAND_RESUME)
        elif bytes_to_write == '!':  # Pause.
            interpreter.realtime_command(COMMAND_PAUSE)
        elif bytes_to_write == '\x18':  # Soft reset.
            interpreter.realtime_command(COMMAND_RESET)

    def write(self, data):
        ord_a = ord('a')
        ord_A = ord('A')
        ord_z = ord('z')
        ord_Z = ord('Z')
        for b in data:
            c = chr(b)
            if c == '?' or c == '~' or c == '!' or c == '\x18':
                self.realtime_write(c)  # Pick off realtime commands.
                continue
            is_end = c == '\n' or c == '\r'
            if self.comment is not None:
                if b == ord(')') or is_end:
                    self.command_map['comment'] = self.comment
                    self.comment = None
                    if not is_end:
                        continue
                else:
                    try:
                        self.comment += str(c)
                    except UnicodeDecodeError:
                        pass  # skip utf8 fail
                    continue
            if b == ord('('):
                self.comment = ""
                continue
            elif b == ord(';'):
                self.comment = ""
                continue
            elif b == ord('\t'):
                continue
            elif b == ord(' '):
                continue
            elif b == ord('/') and len(self.code) == 0:
                continue
            if ord('0') <= b <= ord('9') \
                    or b == ord('+') \
                    or b == ord('-') \
                    or b == ord('.'):
                self.value += chr(b)
                continue

            if ord_A <= b <= ord_Z:  # make lowercase.
                b = b - ord_A + ord_a
                c = chr(b)

            is_letter = ord_a <= b <= ord_z
            if (is_letter or is_end) and len(self.code) != 0:
                if self.code != "" and self.value != "":
                    self.command_map[self.code] = float(self.value)
                self.code = ""
                self.value = ""
            if is_letter:
                self.code += str(c)
                continue
            elif is_end:
                self.command(self.command_map)  # Execute GCode.
                self.read_info = "ok\r\n"
                self.command_map = {}
                self.code = ""
                self.value = ""
                continue

    def read(self, size=-1):
        r = self.read_info
        self.read_info = None
        return r

    def command(self, gc):
        if len(self.command_map) == 0:
            return
        interpreter = self.kernel.device.interpreter
        if 'comment' in gc:
            comment = gc['comment']
            pass
        if 'f' in gc:  # Feed_rate
            v = gc['f']
            feed_rate = self.feed_scale * v
            interpreter.command(COMMAND_SET_SPEED, feed_rate)
        if 's' in gc:
            v = gc['s']
            interpreter.command(COMMAND_SET_POWER, v)
        if 'g' in gc:
            g_value = gc['g']
            if g_value == 0.0:
                self.move_mode = 0
            elif g_value == 1.0:
                self.move_mode = 1
            elif g_value == 2.0:  # CW_ARC
                self.move_mode = 2
            elif g_value == 3.0:  # CCW_ARC
                self.move_mode = 3
            elif gc['g'] == 4.0:  # DWELL
                interpreter.command(COMMAND_MODE_DEFAULT)
                interpreter.command(COMMAND_WAIT_BUFFER_EMPTY)
                if 'p' in gc:
                    p = float(gc['p'])
                    interpreter.command(COMMAND_WAIT, p)
                if 's' in gc:
                    s = float(gc['s'])
                    interpreter.command(COMMAND_WAIT, s)
            elif gc['g'] == 28.0:
                interpreter.command(COMMAND_MODE_DEFAULT)
                interpreter.command(COMMAND_WAIT_BUFFER_EMPTY)
                interpreter.command(COMMAND_HOME)
            elif gc['g'] == 21.0 or gc['g'] == 71.0:
                self.scale = 39.3701  # g20 is mm mode. 39.3701 mils in a mm
            elif gc['g'] == 20.0 or gc['g'] == 70.0:
                self.scale = 1000.0  # g20 is inch mode. 1000 mils in an inch
            elif gc['g'] == 90.0:
                interpreter.command(COMMAND_SET_ABSOLUTE)
            elif gc['g'] == 91.0:
                interpreter.command(COMMAND_SET_INCREMENTAL)
            elif gc['g'] == 94.0:
                # Feed Rate in Units / Minute
                self.feed_scale = (self.scale / MILS_PER_MM) * (1.0 / 60.0)  # units to mm, seconds to minutes.
        if 'm' in gc:
            v = gc['m']
            if v == 30:
                return
            if v == 3 or v == 4:
                self.on_mode = True
            elif v == 5:
                self.on_mode = False
                interpreter.command(COMMAND_LASER_OFF)
        if 'x' in gc or 'y' in gc:
            if self.move_mode == 0:
                interpreter.command(COMMAND_LASER_OFF)
                interpreter.command(COMMAND_MODE_DEFAULT)
            elif self.move_mode == 1 or self.move_mode == 2 or self.move_mode == 3:
                interpreter.command(COMMAND_MODE_COMPACT)
            if 'x' in gc:
                x = gc['x'] * self.scale * self.flip_x
            else:
                x = 0
            if 'y' in gc:
                y = gc['y'] * self.scale * self.flip_y
            else:
                y = 0
            if self.move_mode == 0:
                interpreter.command(COMMAND_LASER_OFF)
                interpreter.command(COMMAND_MOVE, (x, y))
            elif self.move_mode == 1:
                if self.on_mode:
                    interpreter.command(COMMAND_LASER_ON)
                interpreter.command(COMMAND_MOVE, (x, y))
            elif self.move_mode == 2:
                interpreter.command(COMMAND_MOVE, (x, y))  # TODO: Implement CW_ARC
            elif self.move_mode == 3:
                interpreter.command(COMMAND_MOVE, (x, y))  # TODO: Implement CCW_ARC


class SVGWriter:
    def __init__(self):
        self.kernel = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        kernel.add_saver("SVGWriter", self)

    def shutdown(self, kernel):
        self.kernel = None
        del kernel.modules['SVGWriter']

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
        for element in elements:
            if isinstance(element, Path):
                subelement = SubElement(root, SVG_TAG_PATH)
                subelement.set(SVG_ATTR_DATA, element.d())
                subelement.set(SVG_ATTR_TRANSFORM, scale)
                for key, val in element.values.items():
                    if key in ('stroke-width', 'fill-opacity', 'speed',
                               'overscan', 'power', 'id', 'passes',
                               'raster_direction', 'raster_step', 'd_ratio'):
                        subelement.set(key, str(val))
            elif isinstance(element, SVGText):
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
            else:  # Image.
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
        self.kernel = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        kernel.setting(int, "bed_width", 320)
        kernel.setting(int, "bed_height", 220)
        kernel.add_loader("SVGLoader", self)

    def shutdown(self, kernel):
        self.kernel = None
        del kernel.modules['SVGLoader']

    def load_types(self):
        yield "Scalable Vector Graphics", ("svg",), "image/svg+xml"

    def load(self, pathname):
        elements = []
        basename = os.path.basename(pathname)
        scale_factor = 1000.0 / 96.0
        svg = SVG(pathname).elements(width='%fmm' % (self.kernel.bed_width),
                                     height='%fmm' % (self.kernel.bed_height),
                                     ppi=96.0,
                                     transform='scale(%f)' % scale_factor)
        for element in svg:
            if isinstance(element, SVGText):
                elements.append(element)
            elif isinstance(element, Path):
                elements.append(element)
            elif isinstance(element, Shape):
                e = Path(element)
                e.reify()  # In some cases the shape could not have reified, the path must.
                elements.append(e)
            elif isinstance(element, SVGImage):
                try:
                    element.load(os.path.dirname(pathname))
                    if element.image is not None:
                        elements.append(element)
                except OSError:
                    pass
        return elements, pathname, basename


class EgvLoader:
    def __init__(self):
        self.kernel = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        kernel.add_loader("EGVLoader", self)

    def shutdown(self, kernel):
        self.kernel = None
        del kernel.modules['EgvLoader']

    def load_types(self):
        yield "Engrave Files", ("egv",), "application/x-egv"

    def load(self, pathname):
        elements = []
        basename = os.path.basename(pathname)

        for event in parse_egv(pathname):
            path = event['path']
            if len(path) > 0:
                elements.append(path)
                if 'speed' in event:
                    path.values['speed'] = event['speed']
            if 'raster' in event:
                raster = event['raster']
                image = raster.get_image()
                if image is not None:
                    elements.append(image)
                    if 'speed' in event:
                        image.values['speed'] = event['speed']
        return elements, pathname, basename


class ImageLoader:
    def __init__(self):
        self.kernel = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        kernel.add_loader("ImageLoader", self)

    def shutdown(self, kernel):
        self.kernel = None
        del kernel.modules['ImageLoader']

    def load_types(self):
        yield "Portable Network Graphics", ("png",), "image/png"
        yield "Bitmap Graphics", ("bmp",), "image/bmp"
        yield "EPS Format", ("eps",), "image/eps"
        yield "GIF Format", ("gif",), "image/gif"
        yield "Icon Format", ("ico",), "image/ico"
        yield "JPEG Format", ("jpg", "jpeg", "jpe"), "image/jpeg"
        yield "Webp Format", ("webp",), "image/webp"

    def load(self, pathname):
        basename = os.path.basename(pathname)

        image = SVGImage({'href': pathname, 'width': "100%", 'height': "100%"})
        image.load()
        return [image], pathname, basename


class DxfLoader:
    def __init__(self):
        self.kernel = None

    def initialize(self, kernel, name=None):
        self.kernel = kernel
        kernel.add_loader("DxfLoader", self)

    def shutdown(self, kernel):
        self.kernel = None
        del kernel.modules['DxfLoader']

    def load_types(self):
        yield "Drawing Exchange Format", ("dxf",), "image/vnd.dxf"

    def load(self, pathname):
        import ezdxf
        basename = os.path.basename(pathname)
        dxf = ezdxf.readfile(pathname)
        elements = []
        for entity in dxf.entities:
            try:
                entity.transform_to_wcs()
            except AttributeError:
                pass
            if entity.dxftype() == 'CIRCLE':
                element = Circle(center=entity.center, r=entity.radius)
            elif entity.dxftype() == 'ARC':
                element = Path(Arc(center=entity.center,
                                   r=entity.radius,
                                   start_angle=Angle.degrees(dxf.start_angle),
                                   end_angle=Angle.degrees(dxf.end_angle)))
            elif entity.dxftype() == 'ELLIPSE':
                element = Ellipse(center=entity.center,
                                  # major axis is vector
                                  # ratio is the ratio of major to minor.
                                  start_point=dxf.start_point,
                                  end_point=dxf.end_point,
                                  start_angle=dxf.start_param,
                                  end_angle=dxf.end_param)
            elif entity.dxftype() == 'LINE':
                #  https://ezdxf.readthedocs.io/en/stable/dxfentities/line.html
                try:
                    element = SimpleLine(x0=entity.start[0], y0=entity.start[1], x1=entity.end[0], y1=entity.end[1])
                except AttributeError:
                    continue  # Why doesn't this have a start and end. I was it should.
            elif entity.dxftype() == 'LWPOLYLINE':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/lwpolyline.html
                if entity.closed:
                    points = list(entity)
                    element = Polygon(*list((p[0], p[1]) for p in points))
                else:
                    points = list(entity)
                    element = Polyline(*list((p[0], p[1]) for p in points))
                # TODO: If bulges are defined they should be included as arcs.
            elif entity.dxftype() == 'HATCH':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html
                element = Path()
                if entity.bgcolor is not None:
                    Path.fill = Color(entity.bgcolor)
                for p in entity.paths:
                    if p.path_type_flags & 2:
                        for v in p.vertices:
                            element.line(v[0], v[1])
                        if p.is_closed:
                            element.closed()
                    else:
                        for e in p.edges:
                            if type(e) == "LineEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.LineEdge
                                element.line(e.start, e.end)
                            elif type(e) == "ArcEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.ArcEdge
                                element += Arc(center=e.center,
                                               radius=e.radius,
                                               start_angle=Angle.degrees(e.start_angle),
                                               end_angle=Angle.degrees(e.end_angle),
                                               ccw=e.is_counter_clockwise)
                            elif type(e) == "EllipseEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.EllipseEdge
                                element += Arc(radius=e.radius,
                                               start_angle=Angle.degrees(e.start_angle),
                                               end_angle=Angle.degrees(e.end_angle),
                                               ccw=e.is_counter_clockwise)
                            elif type(e) == "SplineEdge":
                                # https://ezdxf.readthedocs.io/en/stable/dxfentities/hatch.html#ezdxf.entities.SplineEdge
                                if e.degree == 3:
                                    for i in range(len(e.knot_values)):
                                        control = e.control_values[i]
                                        knot = e.knot_values[i]
                                        element.quad(control, knot)
                                elif e.degree == 4:
                                    for i in range(len(e.knot_values)):
                                        control1 = e.control_values[2 * i]
                                        control2 = e.control_values[2 * i + 1]
                                        knot = e.knot_values[i]
                                        element.cubic(control1, control2, knot)
                                else:
                                    for i in range(len(e.knot_values)):
                                        knot = e.knot_values[i]
                                        element.line(knot)
            elif entity.dxftype() == 'IMAGE':
                bottom_left_position = entity.insert
                size = entity.image_size
                imagedef = entity.image_def_handle
                element = SVGImage(href=imagedef.filename,
                                   x=bottom_left_position[0],
                                   y=bottom_left_position[1] - size[1],
                                   width=size[0],
                                   height=size[1])
            elif entity.dxftype() == 'MTEXT':
                insert = entity.insert
                element = SVGText(x=insert[0], y=insert[1], text=entity.text)
            elif entity.dxftype() == 'TEXT':
                insert = entity.insert
                element = SVGText(x=insert[0], y=insert[1], text=entity.text)
            elif entity.dxftype() == 'POLYLINE':
                if entity.is_2d_polyline():
                    if entity.is_closed:
                        element = Polygon(entity.points())
                    else:
                        element = Polyline(entity.points())
            elif entity.dxftype() == 'SOLID' or entity.dxftype() == 'TRACE':
                # https://ezdxf.readthedocs.io/en/stable/dxfentities/solid.html
                element = Path(entity)
                element.closed()
                element.fill = Color('Black')
            elif entity.dxftype() == 'SPLINE':
                element = Path()

                if entity.degree == 3:
                    for i in range(entity.n_fit_points):
                        element.quad(
                            entity.control_points[i],
                            entity.fit_point[i]
                        )
                elif entity.degree == 4:
                    for i in range(entity.n_fit_points):
                        element.quad(
                            entity.control_points[2*i],
                            entity.control_points[2 * i + 1],
                            entity.fit_point[i]
                        )
                else:
                    for i in range(entity.n_fit_points):
                        element.line(entity.fit_point[i])
            else:
                continue
                # Might be something unsupported.
            if entity.rgb is not None:
                element.stroke = Color(entity.rgb)
            else:
                element.stroke = Color('black')
            elements.append(Path(element))

        return elements, pathname, basename
