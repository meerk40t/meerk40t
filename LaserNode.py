from LaserCommandConstants import *
from RasterPlotter import RasterPlotter, X_AXIS, TOP, BOTTOM
from svgelements import *

"""
 Tree building class for projects. This class is intended to take SVGElement class objects and give them a MeerK40t
 presentation as well as the methods for turning these objects into functional commands to be executed by a writer.
"""

VARIABLE_NAME_TYPE = 'type'
VARIABLE_NAME_NAME = 'name'
VARIABLE_NAME_STROKE_COLOR = 'stroke'
VARIABLE_NAME_FILL_COLOR = 'fill'
VARIABLE_NAME_SPEED = 'speed'
VARIABLE_NAME_POWER = 'power'
VARIABLE_NAME_PASSES = 'passes'
VARIABLE_NAME_DRATIO = 'd_ratio'
VARIABLE_NAME_RASTER_STEP = 'raster_step'
VARIABLE_NAME_RASTER_DIRECTION = 'raster_direction'


class LaserNode(list):
    """
    LaserNodes wrap an SVGElement. And maintains an tree like datastructure which is converted
    into code to be processed by the LhymicroWriter or any compatible writer.

    All LaserNodes contain:
    'parent' refers to the parent object.
    'element' contains a SVGElement classed object.
    'cache' contains cached information for the project render.
    'scene_bounds' contain the object's bounds within the scene.
    """

    def __init__(self, element=None, parent=None):
        list.__init__(self)
        if isinstance(element, LaserNode):
            e = element.element
            if isinstance(e, Path):
                element = Path(e)
            elif isinstance(e, SVGImage):
                element = SVGImage(e)
            elif isinstance(e, SVGText):
                element = SVGText(e)
            elif isinstance(e, SVGElement):
                element = SVGElement(e)
            else:
                element = SVGElement()
        self.parent = parent
        self.cache = None
        self.scene_bounds = None
        if element is not None:
            if not isinstance(element, SVGElement):
                raise ValueError('Must be SVGElement classed object')
            self.element = element
        else:
            self.element = SVGElement()
        if self.speed is not None:
            self.speed = float(self.speed)
        else:
            if isinstance(element, SVGImage):
                self.speed = 150.0
            else:
                self.speed = 20.0
        if self.passes is not None:
            self.passes = int(self.passes)
        else:
            self.passes = 1
        if self.power is not None:
            self.power = float(self.power)
        else:
            self.power = 1000.0
        if self.raster_step is not None:
            self.raster_step = int(self.raster_step)
        else:
            self.raster_step = 1
        if self.raster_direction is not None:
            self.raster_direction = int(self.raster_direction)
        else:
            self.raster_direction = 0

        if self.stroke is None or self.stroke == 'none':
            if isinstance(element, SVGElement):
                self.stroke = Color('blue')
            elif isinstance(element, SVGText):
                self.stroke = Color('black')
            else:
                self.stroke = Color('green')
        # if isinstance(element, SVGImage):
        #     # Converting all images to RGBA.
        #     element.image = element.image.convert("RGBA")
        elif isinstance(element, SVGText):
            # Converting x and y value into matrix values.
            self.transform.pre_translate(element.x, element.y)
            self.element.x = 0
            self.element.y = 0

    def __eq__(self, other):
        return other is self

    def __setitem__(self, key, value):
        try:
            self.element.values[key] = value
        except AttributeError:
            self.element.values = {key: value}

    def __getitem__(self, item):
        if isinstance(item, tuple):
            try:
                return self.element.values[item[0]]
            except KeyError:
                return item[1]
        try:
            return self.element.values[item]
        except KeyError:
            return None
        except AttributeError:
            return None

    def __str__(self):
        name = self.name
        if name is not None:
            return name
        if self.parent is None or not isinstance(self.parent, LaserNode):
            return "Project"
        if len(self) != 0:
            name = "Group"
            if self.element is not None:
                return "%d pass, %s" % (self.passes, name)
            return name
        if isinstance(self.element, SVGImage):
            id = self.id
            if id is None:
                id = "Image"
            else:
                id = str(id)
            wi = self.element.image_width
            hi = self.element.image_height
            bbox = self.element.bbox()
            wr = bbox[2] - bbox[1]
            hr = bbox[3] - bbox[0]
            m = self.transform
            s = self.raster_step
            if m.a == s and m.b == 0.0 and m.c == 0.0 and m.d == s:
                return "%s %dx%d %d@%3f" % (id, wi, hi, self.raster_step, self.speed)
            else:
                return "*** %s (%dx%d) -> (%dx%d) %d@%3f" % (id, wi, hi, wr, hr, self.raster_step, self.speed)
        if isinstance(self.element, SVGText):
            string = "NOT IMPLEMENTED: \"%s\"" % (self.element.text)
            if len(string) < 100:
                return string
            return string[:97] + '...'
        if isinstance(self.element, Path):
            try:
                h = str(hash(self.element.d()))
            except TypeError:
                h = "None"
            name = "Path @%.1f mm/s %.1fx path=%s" % \
                   (self.speed,
                    self.element.transform.value_scale_x(),
                    h)
            if len(name) >= 100:
                name = name[:97] + '...'
            return name
        return 'unknown'

    @property
    def type(self):
        if self.parent is None or not isinstance(self.parent, LaserNode):
            return 'root'
        if len(self) > 0:
            return 'group'
        if isinstance(self.element, Path):
            return 'path'
        if isinstance(self.element, SVGImage):
            return 'image'
        if isinstance(self.element, SVGText):
            return 'text'
        return 'node'

    @property
    def passes(self):
        return self[VARIABLE_NAME_PASSES]

    @passes.setter
    def passes(self, value):
        self[VARIABLE_NAME_PASSES] = value

    @property
    def name(self):
        return self[VARIABLE_NAME_NAME]

    @name.setter
    def name(self, value):
        self[VARIABLE_NAME_NAME] = value

    @property
    def speed(self):
        return self[VARIABLE_NAME_SPEED]

    @speed.setter
    def speed(self, value):
        self[VARIABLE_NAME_SPEED] = value

    @property
    def dratio(self):
        return self[VARIABLE_NAME_DRATIO]

    @dratio.setter
    def dratio(self, value):
        self[VARIABLE_NAME_DRATIO] = value

    @property
    def power(self):
        return self[VARIABLE_NAME_POWER]

    @power.setter
    def power(self, value):
        self[VARIABLE_NAME_POWER] = value

    @property
    def raster_step(self):
        v = self[VARIABLE_NAME_RASTER_STEP]
        if isinstance(v, str):
            v = int(v)
        return v

    @raster_step.setter
    def raster_step(self, value):
        self[VARIABLE_NAME_RASTER_STEP] = value

    @property
    def raster_direction(self):
        return self[VARIABLE_NAME_RASTER_DIRECTION]

    @raster_direction.setter
    def raster_direction(self, value):
        self[VARIABLE_NAME_RASTER_DIRECTION] = value

    @property
    def stroke_width(self):
        v = self['stroke-width']
        sw = 1000 / 96.0
        if v is None:
            return sw
        v = Length(v).value(ppi=96.0)
        if isinstance(v, Length):
            return sw
        else:
            return v * sw

    @stroke_width.setter
    def stroke_width(self, value):
        self['stroke-width'] = value

    @property
    def stroke(self):
        try:
            return self.element.stroke
        except AttributeError:
            return None

    @stroke.setter
    def stroke(self, value):
        self.element.stroke = Color(value)

    @property
    def fill(self):
        try:
            return self.element.fill
        except AttributeError:
            return None

    @fill.setter
    def fill(self, value):
        self.element.fill = Color(value)

    @property
    def id(self):
        try:
            return self.element.id
        except AttributeError:
            return None

    @id.setter
    def id(self, value):
        self.element.id = value

    @property
    def transform(self):
        try:
            return self.element.transform
        except AttributeError:
            return Matrix()

    @transform.setter
    def transform(self, value):
        self.element.transform = value

    @property
    def center(self):
        if self.scene_bounds is None:
            if self.element is None:
                return None
            else:
                try:
                    self.scene_bounds = self.element.bbox()
                except AttributeError:
                    return None
                if self.scene_bounds is None:
                    return None
        return (self.scene_bounds[2] - self.scene_bounds[0]) / 2.0, (self.scene_bounds[3] - self.scene_bounds[1]) / 2.0

    def generate(self):
        if isinstance(self.element, SVGImage):
            for g in self.generate_image():
                yield g
        elif isinstance(self.element, Path):
            for g in self.generate_path():
                yield g
        elif isinstance(self.element, SVGText):
            for g in self.generate_text():
                yield g

    def generate_text(self):
        yield COMMAND_MODE_DEFAULT, 0

    def generate_path(self):
        object_path = abs(self.element)
        yield COMMAND_SET_SPEED, self.speed
        yield COMMAND_SET_POWER, self.power
        yield COMMAND_SET_D_RATIO, self.dratio
        plot = object_path
        first_point = plot.first_point
        if first_point is None:
            return
        yield COMMAND_RAPID_MOVE, first_point
        yield COMMAND_SET_STEP, 0
        yield COMMAND_MODE_COMPACT, 0
        yield COMMAND_PLOT, plot
        yield COMMAND_MODE_DEFAULT, 0
        yield COMMAND_SET_SPEED, None
        yield COMMAND_SET_D_RATIO, None

    def generate_image(self):
        image = self.element.image
        yield COMMAND_SET_SPEED, self.speed

        direction = self.raster_direction
        step = self.raster_step
        yield COMMAND_SET_POWER, self.power

        traverse = 0
        if direction == 0:
            yield COMMAND_SET_STEP, step
            traverse |= X_AXIS
            traverse |= TOP
        elif direction == 1:
            yield COMMAND_SET_STEP, step
            traverse |= X_AXIS
            traverse |= BOTTOM
        width, height = image.size
        mode = image.mode

        if mode != "1" and mode != "P" and mode != "L" and mode != "RGB" and mode != "RGBA":
            # Any mode without a filter should get converted.
            image = self.element.image = image.convert("RGBA")
            mode = image.mode
        if mode == "1":
            def image_filter(pixel):
                return (255 - pixel) / 255.0
        elif mode == "P":
            p = image.getpalette()

            def image_filter(pixel):
                v = p[pixel * 3] + p[pixel * 3 + 1] + p[pixel * 3 + 2]
                return 1.0 - v / 765.0
        elif mode == "L":
            def image_filter(pixel):
                return (255 - pixel) / 255.0
        elif mode == "RGB":
            def image_filter(pixel):
                return 1.0 - (pixel[0] + pixel[1] + pixel[2]) / 765.0
        elif mode == "RGBA":
            def image_filter(pixel):
                return (1.0 - (pixel[0] + pixel[1] + pixel[2]) / 765.0) * pixel[3] / 255.0
        else:
            raise ValueError  # this shouldn't happen.
        m = self.transform
        data = image.load()
        overscan = self['overscan']
        if overscan is None:
            overscan = 20
        else:
            try:
                overscan = int(overscan)
            except ValueError:
                overscan = 20
        raster = RasterPlotter(data, width, height, traverse, 0, overscan,
                               m.value_trans_x(),
                               m.value_trans_y(),
                               step, image_filter)
        yield COMMAND_RAPID_MOVE, raster.initial_position_in_scene()
        yield COMMAND_SET_DIRECTION, raster.initial_direction()
        yield COMMAND_MODE_COMPACT, 0
        yield COMMAND_RASTER, raster
        yield COMMAND_MODE_DEFAULT, 0

    def append_all(self, obj_list):
        """Group append to trigger the notification only once."""
        for obj in obj_list:
            if obj.parent is not None:
                raise ValueError("Still has a parent.")
            if obj in self:
                raise ValueError("Already part of list.")
            list.append(self, obj)
            obj.parent = self
        self.notify_change()

    def append(self, obj):
        if obj.parent is not None:
            raise ValueError("Still has a parent.")
        if obj in self:
            raise ValueError("Already part of list.")
        list.append(self, obj)
        obj.parent = self
        self.notify_change()

    def remove(self, obj):
        list.remove(self, obj)
        obj.parent = None
        self.notify_change()

    def detach(self):
        if self.parent is not None:
            self.parent.remove(self)

    def notify_change(self):
        if self.parent == self:
            raise ValueError
        if self.parent is not None:
            self.parent.notify_change()

    def contains(self, x, y=None):
        if y is None:
            x, y = x
        if self.scene_bounds is None:
            if self.element is None:
                return False
            else:
                try:
                    self.scene_bounds = self.element.bbox()
                except AttributeError:
                    return False
                if self.scene_bounds is None:
                    return False
        return self.scene_bounds[0] <= x <= self.scene_bounds[2] and self.scene_bounds[1] <= y <= self.scene_bounds[3]

    def flat_elements(self, types=None, passes=True):
        if types is None:
            types = ('image', 'path', 'text')
        pass_count = self.passes
        if not passes:
            pass_count = 1
        for i in range(0, pass_count):
            if self.type in (types):
                yield self
            for element in self:
                for flat_element in element.flat_elements(types=types, passes=passes):
                    yield flat_element

    def all_children_of_type(self, types):
        if self.type in types:
            return [self]
        return [e for e in self if e.type in types]

    def contains_type(self, types):
        results = self.all_children_of_type(types)
        return len(results) != 0

    def convert_absolute_to_affinespace(self, position):
        if self.element is not None:
            try:
                return self.transform.point_in_matrix_space(position)
            except AttributeError:
                return position

    def convert_affinespace_to_absolute(self, position):
        if self.element is not None:
            try:
                return self.transform.point_in_inverse_space(position)
            except AttributeError:
                return position

    def move(self, dx, dy):
        if self.element is not None:
            try:
                self.transform.post_translate(dx, dy)  # Apply translate after all the other events.
            except AttributeError:
                pass
            self.scene_bounds = None

    def reify_matrix(self):
        """Apply the matrix to the path and reset matrix."""
        self.element = abs(self.element)
        self.scene_bounds = None

    def needs_actualization(self):
        if self.type != 'image':
            return False
        m = self.transform
        s = self.raster_step
        return m.a != s or m.b != 0.0 or m.c != 0.0 or m.d != s

    def set_native(self):
        tx = self.transform.value_trans_x()
        ty = self.transform.value_trans_y()
        step = float(self.raster_step)

        self.transform.reset()
        self.transform.post_scale(step, step)
        self.transform.post_translate(tx, ty)
        step = float(self.raster_step)
        self.transform.pre_scale(step, step)

    def make_actual(self):
        """
        Makes PIL image actual in that it manipulates the pixels to actually exist
        rather than simply apply the transform on the image to give the resulting image.
        Since our goal is to raster the images real pixels this is required.

        SVG matrices are defined as follows.
        [a c e]
        [b d f]

        Pil requires a, c, e, b, d, f accordingly.
        """
        if not isinstance(self.element, SVGImage):
            return

        from PIL import Image

        image = self.element.image
        self.cache = None
        m = self.transform
        step = float(self.raster_step)

        tx = m.value_trans_x()
        ty = m.value_trans_y()
        m.e = 0.0
        m.f = 0.0
        self.element.transform.pre_scale(1.0 / step, 1.0 / step)
        bbox = self.element.bbox()
        width = int(ceil(bbox[2] - bbox[0]))
        height = int(ceil(bbox[3] - bbox[1]))
        m.inverse()
        image = image.transform((width, height), Image.AFFINE, (m.a, m.c, m.e, m.b, m.d, m.f),
                                resample=Image.BICUBIC)
        self.transform.reset()
        self.transform.post_scale(step, step)
        self.transform.post_translate(tx, ty)
        self.element.image = image
        self.element.image_width = width
        self.element.image_height = height
        self.scene_bounds = None

    def update(self, element):
        if isinstance(element, LaserNode):
            try:
                self.element.values.update(element.values)
            except AttributeError:
                pass
        elif isinstance(element, dict):
            try:
                self.element.values.update(element)
            except AttributeError:
                pass
