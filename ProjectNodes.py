from svg.elements import *

from LaserCommandConstants import *
from RasterPlotter import RasterPlotter, X_AXIS, TOP, BOTTOM

"""
Project Nodes is a tree based set of wrappers for various objects which are converted into code to be processed by the 
LhymicroWriter or any compatible writer.

Each element wraps its respective object and provides a generate function as well as a properties dict. 
"""

VARIABLE_NAME_TYPE = 'type'
VARIABLE_NAME_NAME = 'name'
VARIABLE_NAME_COLOR = 'color'
VARIABLE_NAME_FILL_COLOR = 'fill'
VARIABLE_NAME_SPEED = 'speed'
VARIABLE_NAME_POWER = 'power'
VARIABLE_NAME_PASSES = 'passes'
VARIABLE_NAME_DRATIO = 'd_ratio'
VARIABLE_NAME_RASTER_STEP = 'raster_step'
VARIABLE_NAME_RASTER_DIRECTION = 'raster_direction'


class LaserNode(list):
    def __init__(self):
        list.__init__(self)
        self.element = None
        self.properties = {}
        self.parent = None
        self.box = None
        self.bounds = None

    def __eq__(self, other):
        return other is self

    @property
    def passes(self):
        if VARIABLE_NAME_PASSES in self.properties:
            return self.properties[VARIABLE_NAME_PASSES]
        return 1

    @property
    def name(self):
        if VARIABLE_NAME_NAME in self.properties:
            return self.properties[VARIABLE_NAME_NAME]
        return str(self)

    @property
    def speed(self):
        if VARIABLE_NAME_SPEED in self.properties:
            return self.properties[VARIABLE_NAME_SPEED]
        return 20

    @property
    def power(self):
        if VARIABLE_NAME_POWER in self.properties:
            return self.properties[VARIABLE_NAME_POWER]
        return 1000

    @property
    def stroke(self):
        if VARIABLE_NAME_COLOR in self.properties:
            return self.properties[VARIABLE_NAME_COLOR]
        return None

    @property
    def fill(self):
        if VARIABLE_NAME_FILL_COLOR in self.properties:
            return self.properties[VARIABLE_NAME_FILL_COLOR]
        return None

    def set_color(self, color):
        self.properties[VARIABLE_NAME_COLOR] = color

    def generate(self, dc):
        pass

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
        if self.bounds is None:
            return False
        return self.bounds[0] <= x <= self.bounds[2] and self.bounds[1] <= y <= self.bounds[3]

    def flat_elements(self, types=None, passes=False):
        if types is None:
            types = LaserNode
        pass_count = self.passes
        for i in range(0, pass_count):
            if isinstance(self, types):
                yield self
            for element in self:
                for flat_element in element.flat_elements(types=types):
                    yield flat_element

    def all_children_of_type(self, types):
        if isinstance(self, types):
            return [self]
        return [e for e in self if isinstance(e, types)]

    def contains_type(self, types):
        results = self.all_children_of_type(types)
        return len(results) != 0

    @property
    def center(self):
        return (self.bounds[2] - self.bounds[0]) / 2.0, (self.bounds[3] - self.bounds[1]) / 2.0


class LaserGroup(LaserNode):
    def __init__(self):
        LaserNode.__init__(self)

    def __str__(self):
        if VARIABLE_NAME_NAME in self.properties:
            return self.properties[VARIABLE_NAME_NAME]
        name = "Group"
        if VARIABLE_NAME_PASSES in self.properties:
            return "%d pass, %s" % (self.properties[VARIABLE_NAME_PASSES], name)
        else:
            return name


class LaserElement(LaserNode):
    def __init__(self):
        LaserNode.__init__(self)
        self.element = None
        self.properties = {VARIABLE_NAME_COLOR: 0,
                           VARIABLE_NAME_FILL_COLOR: 0,
                           VARIABLE_NAME_SPEED: 60,
                           VARIABLE_NAME_PASSES: 1,
                           VARIABLE_NAME_POWER: 1000.0}

    def set_color(self, color):
        self.properties[VARIABLE_NAME_COLOR] = color

    def generate(self, m=None):
        yield COMMAND_MODE_DEFAULT, 0

    def convert_absolute_to_affinespace(self, position):
        if self.element is not None:
            try:
                return self.element.transform.point_in_matrix_space(position)
            except AttributeError:
                return position

    def convert_affinespace_to_absolute(self, position):
        if self.element is not None:
            try:
                return self.element.transform.point_in_inverse_space(position)
            except AttributeError:
                return position

    def move(self, dx, dy):
        if self.element is not None:
            try:
                self.element.transform.post_translate(dx, dy)   # Apply translate after all the other events.
            except AttributeError:
                pass

    def reify_matrix(self):
        """Apply the matrix to the path and reset matrix."""
        self.element = abs(self.element)


class ImageElement(LaserElement):
    def __init__(self, image_element):
        LaserElement.__init__(self)
        self.box = image_element.bbox()
        self.box = [0, 0, image_element.image_width, image_element.image_height]
        self.element = image_element
        # Converting all images to RGBA.
        image_element.image = image_element.image.convert("RGBA")
        self.cache = None
        self.properties.update({VARIABLE_NAME_RASTER_STEP: 1,
                                VARIABLE_NAME_SPEED: 100,
                                VARIABLE_NAME_POWER: 1000.0})

    def __str__(self):
        if VARIABLE_NAME_NAME in self.properties:
            return self.properties[VARIABLE_NAME_NAME]
        return "Image %dX s@%3f" % (self.properties[VARIABLE_NAME_RASTER_STEP],
                                    self.properties[VARIABLE_NAME_SPEED])

    def set_native(self):
        tx = self.element.transform.value_trans_x()
        ty = self.element.transform.value_trans_y()
        self.element.transform.reset()
        self.element.transform.post_translate(tx, ty)
        if VARIABLE_NAME_RASTER_STEP in self.properties:
            step = float(self.properties[VARIABLE_NAME_RASTER_STEP])
            self.element.transform.pre_scale(step, step)

    def make_actual(self):
        image = self.element.image
        e.cache = None
        tx = self.element.transform.value_trans_x()
        ty = self.element.transform.value_trans_y()
        self.element.transform.reset()
        self.element.transform.post_translate(tx, ty)
        if VARIABLE_NAME_RASTER_STEP in self.properties:
            step = float(self.properties[VARIABLE_NAME_RASTER_STEP])
            self.element.transform.pre_scale(step, step)
        self.element = image
        #todo: set bounds by value again.

    def generate(self, m=None):
        if m is None:
            m = self.element.transform
        image = self.element.image
        speed = 100
        if VARIABLE_NAME_SPEED in self.properties:
            speed = self.properties[VARIABLE_NAME_SPEED]
        if speed is None:
            speed = 100
        yield COMMAND_SET_SPEED, speed

        direction = 0
        if VARIABLE_NAME_RASTER_DIRECTION in self.properties:
            direction = self.properties[VARIABLE_NAME_RASTER_DIRECTION]
        step = 1
        if VARIABLE_NAME_RASTER_STEP in self.properties:
            step = self.properties[VARIABLE_NAME_RASTER_STEP]
        if VARIABLE_NAME_POWER in self.properties:
            power = self.properties.get(VARIABLE_NAME_POWER)
            yield COMMAND_SET_POWER, power
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
            self.element = self.element.convert("RGBA")
            mode = image.mode
        if mode == "1":
            def image_filter(pixel):
                return (255 - pixel) / 255.0
        elif mode == "P":
            p = self.element.getpalette()

            def image_filter(pixel):
                v = p[pixel * 3] + p[pixel * 3 + 1] + p[pixel * 3 + 2]
                return 1.0 - v / 765.0
        elif mode == "L":
            def image_filter(pixel):
                return (255 - pixel) / 255.0
        elif mode == "RGB" or mode == "RGBA":
            def image_filter(pixel):
                return 1.0 - (pixel[0] + pixel[1] + pixel[2]) / 765.0
        else:
            raise ValueError  # this shouldn't happen.

        data = image.load()
        raster = RasterPlotter(data, width, height, traverse, 0, 20,
                               m.value_trans_x(),
                               m.value_trans_y(),
                               step, image_filter)
        yield COMMAND_RAPID_MOVE, raster.initial_position_in_scene()
        yield COMMAND_SET_DIRECTION, raster.initial_direction()
        yield COMMAND_MODE_COMPACT, 0
        yield COMMAND_RASTER, raster
        yield COMMAND_MODE_DEFAULT, 0


class TextElement(LaserElement):
    def __init__(self, element):
        LaserElement.__init__(self)
        self.element = element
        self.properties.update({VARIABLE_NAME_COLOR: 0x000000, VARIABLE_NAME_SPEED: 20, VARIABLE_NAME_POWER: 1000.0})
        if isinstance(element, SVGText):
            self.element.transform.pre_translate(element.x, element.y)
            self.element.x = 0
            self.element.y = 0
            self.properties[VARIABLE_NAME_FILL_COLOR] = element.fill
            self.properties[VARIABLE_NAME_COLOR] = element.stroke
            self.text = element.text
        else:
            self.text = element

    def __str__(self):
        if VARIABLE_NAME_NAME in self.properties:
            return self.properties[VARIABLE_NAME_NAME]
        string = "NOT IMPLEMENTED: \"%s\"" % (self.text)
        if len(string) < 100:
            return string
        return string[:97] + '...'


class PathElement(LaserElement):
    def __init__(self, element):
        LaserElement.__init__(self)
        self.element = element
        self.properties.update({VARIABLE_NAME_COLOR: 0x00FF00, VARIABLE_NAME_SPEED: 20, VARIABLE_NAME_POWER: 1000.0})
        if isinstance(element, Path):
            self.properties[VARIABLE_NAME_FILL_COLOR] = element.fill
            self.properties[VARIABLE_NAME_COLOR] = element.stroke

    def __str__(self):
        if VARIABLE_NAME_NAME in self.properties:
            return self.properties[VARIABLE_NAME_NAME]
        name = "Path @%.1f mm/s %.1fx path=%s" % \
               (self.properties[VARIABLE_NAME_SPEED],
                self.element.transform.value_scale_x(),
                str(hash(self.element.d())))
        if len(name) >= 100:
            name = name[:97] + '...'
        return name


    def generate(self, m=None):
        object_path = abs(self.element)
        self.box = object_path.bbox()
        if VARIABLE_NAME_SPEED in self.properties:
            speed = self.properties.get(VARIABLE_NAME_SPEED)
            yield COMMAND_SET_SPEED, speed
        if VARIABLE_NAME_POWER in self.properties:
            power = self.properties.get(VARIABLE_NAME_POWER)
            yield COMMAND_SET_POWER, power
        if VARIABLE_NAME_DRATIO in self.properties:
            d_ratio = self.properties.get(VARIABLE_NAME_DRATIO)
            yield COMMAND_SET_D_RATIO, d_ratio
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


class RawElement(LaserElement):
    def __init__(self, element):
        LaserElement.__init__(self)
        self.command_list = []
        for command in element.generate():
            self.command_list.append(command)

    def generate(self, m=None):
        if m is None:
            pass
            # Raw cannot have matrix.
        for command in self.command_list:
            yield command

    def __str__(self):
        if VARIABLE_NAME_NAME in self.properties:
            return self.properties[VARIABLE_NAME_NAME]
        string = "Raw #%d cmd=%s" % \
                 (len(self.command_list), str(self.command_list))
        if len(string) < 100:
            return string
        return string[:97] + '...'


class ProjectRoot(LaserNode):
    def __init__(self):
        LaserNode.__init__(self)

    def __str__(self):
        return "Project"
