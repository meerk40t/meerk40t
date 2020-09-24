from CutPlanner import CutPlanner
from svgelements import *
from LaserCommandConstants import *
from LaserOperation import LaserOperation
from LaserRender import LaserRender


class OperationPreprocessor:

    def __init__(self):
        self.device = None
        self.commands = []
        self.operations = None

    def process(self, operations):
        self.operations = operations
        if self.device.rotary:
            self.conditional_jobadd_scale_rotary()
        self.conditional_jobadd_actualize_image()
        self.conditional_jobadd_make_raster()
        self.conditional_jobadd_optimize_cuts()

    def execute(self):
        # Using copy of commands, so commands can add ops.
        commands = self.commands[:]
        self.commands = []
        for cmd in commands:
            cmd()

    def conditional_jobadd_make_raster(self):
        for op in self.operations:
            try:
                if op.operation == "Raster":
                    if len(op) == 0:
                        continue
                    if len(op) == 1 and isinstance(op[0], SVGImage):
                        continue  # make raster not needed since its a single real raster.
                    self.jobadd_make_raster()
                    return True
            except AttributeError:
                pass
        return False

    def jobadd_make_raster(self):
        def make_image():
            for op in self.operations:
                try:
                    if op.operation == "Raster":
                        if len(op) == 1 and isinstance(op[0], SVGImage):
                            continue
                        renderer = LaserRender(self.device.device_root)
                        bounds = OperationPreprocessor.bounding_box(op)
                        if bounds is None:
                            return None
                        xmin, ymin, xmax, ymax = bounds

                        image = renderer.make_raster(op, bounds, step=op.raster_step)
                        image_element = SVGImage(image=image)
                        image_element.transform.post_translate(xmin, ymin)
                        op.clear()
                        op.append(image_element)
                except AttributeError:
                    pass

        self.commands.append(make_image)

    def conditional_jobadd_optimize_cuts(self):
        for op in self.operations:
            try:
                if op.operation in ("Cut"):
                    self.jobadd_optimize_cuts()
                    return
            except AttributeError:
                pass

    def jobadd_optimize_cuts(self):
        def optimize_cuts():
            for op in self.operations:
                try:
                    if op.operation in ("Cut"):
                        op_cuts = CutPlanner.optimize_cut_inside(op)
                        op.clear()
                        op.append(op_cuts)
                except AttributeError:
                    pass

        self.commands.append(optimize_cuts)

    def conditional_jobadd_actualize_image(self):
        for op in self.operations:
            try:
                if op.operation == "Raster":
                    for elem in op:
                        if OperationPreprocessor.needs_actualization(elem, op.raster_step):
                            self.jobadd_actualize_image()
                            return
                if op.operation == "Image":
                    for elem in op:
                        if OperationPreprocessor.needs_actualization(elem, None):
                            self.jobadd_actualize_image()
                            return
            except AttributeError:
                pass

    def jobadd_actualize_image(self):
        def actualize():
            for op in self.operations:
                try:
                    if op.operation == "Raster":
                        for elem in op:
                            if OperationPreprocessor.needs_actualization(elem, op.raster_step):
                                OperationPreprocessor.make_actual(elem, op.raster_step)
                    if op.operation == "Image":
                        for elem in op:
                            if OperationPreprocessor.needs_actualization(elem, None):
                                OperationPreprocessor.make_actual(elem, None)
                except AttributeError:
                    pass
        self.commands.append(actualize)

    def conditional_jobadd_scale_rotary(self):
        if self.device.scale_x != 1.0 or self.device.scale_y != 1.0:
            self.jobadd_scale_rotary()

    def jobadd_scale_rotary(self):
        def scale_for_rotary():
            p = self.device
            scale_str = 'scale(%f,%f,%f,%f)' % (p.scale_x, p.scale_y, p.current_x, p.current_y)
            for o in self.operations:
                if isinstance(o, LaserOperation):
                    for e in o:
                        try:
                            e *= scale_str
                        except AttributeError:
                            pass
            self.conditional_jobadd_actualize_image()

        self.commands.append(scale_for_rotary)

    @staticmethod
    def origin():
        yield COMMAND_WAIT_FINISH
        yield COMMAND_MODE_RAPID
        yield COMMAND_SET_ABSOLUTE
        yield COMMAND_MOVE, 0, 0

    @staticmethod
    def home():
        yield COMMAND_WAIT_FINISH
        yield COMMAND_HOME

    @staticmethod
    def wait():
        wait_amount = 5.0
        yield COMMAND_WAIT_FINISH
        yield COMMAND_WAIT, wait_amount

    @staticmethod
    def beep():
        yield COMMAND_WAIT_FINISH
        yield COMMAND_BEEP

    @staticmethod
    def needs_actualization(image_element, step_level=None):
        if not isinstance(image_element, SVGImage):
            return False
        if step_level is None:
            if 'raster_step' in image_element.values:
                step_level = float(image_element.values['raster_step'])
            else:
                step_level = 1.0
        m = image_element.transform
        # Transformation must be uniform to permit native rastering.
        return m.a != step_level or m.b != 0.0 or m.c != 0.0 or m.d != step_level

    @staticmethod
    def make_actual(image_element, step_level=None):
        """
        Makes PIL image actual in that it manipulates the pixels to actually exist
        rather than simply apply the transform on the image to give the resulting image.
        Since our goal is to raster the images real pixels this is required.

        SVG matrices are defined as follows.
        [a c e]
        [b d f]

        Pil requires a, c, e, b, d, f accordingly.
        """
        if not isinstance(image_element, SVGImage):
            return
        from PIL import Image

        pil_image = image_element.image
        image_element.cache = None
        matrix = image_element.transform
        bbox = OperationPreprocessor.bounding_box([image_element])
        print(bbox)
        element_width = int(ceil(bbox[2] - bbox[0]))
        element_height = int(ceil(bbox[3] - bbox[1]))
        if step_level is None:
            # If we are not told the step amount either draw it from the object or set it to default.
            if 'raster_step' in image_element.values:
                step_level = float(image_element.values['raster_step'])
            else:
                step_level = 1.0
        step_scale = 1 / float(step_level)
        tx = bbox[0]
        ty = bbox[1]
        matrix.post_translate(-tx, -ty)
        matrix.post_scale(step_scale, step_scale)  # step level requires the actual image be scaled down.
        matrix.inverse()

        if (matrix.value_skew_y() != 0.0 or matrix.value_skew_y() != 0.0) and pil_image.mode != 'RGBA':
            # If we are rotating an image without alpha, we need to convert it, or the rotation invents black pixels.
            pil_image = pil_image.convert('RGBA')

        pil_image = pil_image.transform((element_width, element_height), Image.AFFINE,
                                        (matrix.a, matrix.c, matrix.e, matrix.b, matrix.d, matrix.f),
                                        resample=Image.BICUBIC)
        image_element.image_width, image_element.image_height = (element_width, element_height)
        matrix.reset()

        box = pil_image.getbbox()
        print(box)
        width = box[2] - box[0]
        height = box[3] - box[1]
        if width != element_width and height != element_height:
            image_element.image_width, image_element.image_height = (width, height)
            pil_image = pil_image.crop(box)
            matrix.post_translate(box[0], box[1])
        # step level requires the new actualized matrix be scaled up.
        matrix.post_scale(step_level, step_level)
        matrix.post_translate(tx, ty)
        image_element.image = pil_image

    @staticmethod
    def reify_matrix(self):
        """Apply the matrix to the path and reset matrix."""
        self.element = abs(self.element)
        self.scene_bounds = None

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

    @staticmethod
    def is_inside(inner_path, outer_path):
        """
        Test that path1 is inside path2.
        :param inner_path: inner path
        :param outer_path: outer path
        :return: whether path1 is wholely inside path2.
        """
        if not hasattr(inner_path, 'bounding_box'):
            inner_path.bounding_box = OperationPreprocessor.bounding_box(inner_path)
        if not hasattr(outer_path, 'bounding_box'):
            outer_path.bounding_box = OperationPreprocessor.bounding_box(outer_path)
        if outer_path.bounding_box[0] > inner_path.bounding_box[0]:
            # outer minx > inner minx (is not contained)
            return False
        if outer_path.bounding_box[1] > inner_path.bounding_box[1]:
            # outer miny > inner miny (is not contained)
            return False
        if outer_path.bounding_box[2] < inner_path.bounding_box[2]:
            # outer maxx < inner maxx (is not contained)
            return False
        if outer_path.bounding_box[3] < inner_path.bounding_box[3]:
            # outer maxy < inner maxy (is not contained)
            return False
        if outer_path.bounding_box == inner_path.bounding_box:
            if outer_path == inner_path:  # This is the same object.
                return False
        if not hasattr(outer_path, 'vm'):
            outer_path = Polygon([outer_path.point(i / 100.0, error=1e4) for i in range(101)])
            vm = VectorMontonizer()
            vm.add_cluster(outer_path)
            outer_path.vm = vm
        for i in range(101):
            p = inner_path.point(i / 100.0, error=1e4)
            if not outer_path.vm.is_point_inside(p.x, p.y):
                return False
        return True

    @staticmethod
    def optimize_cut_inside(paths):
        optimized = Path()
        if isinstance(paths, Path):
            paths = [paths]
        subpaths = []
        for path in paths:
            subpaths.extend([abs(Path(s)) for s in path.as_subpaths()])
        for j in range(len(subpaths)):
            for k in range(j+1, len(subpaths)):
                if OperationPreprocessor.is_inside(subpaths[k],subpaths[j]):
                    t = subpaths[j]
                    subpaths[j] = subpaths[k]
                    subpaths[k] = t
        for p in subpaths:
            optimized += p
            try:
                del p.vm
            except AttributeError:
                pass
            try:
                del p.bounding_box
            except AttributeError:
                pass
        return optimized


class VectorMontonizer:
    def __init__(self, low_value=-float('inf'), high_value=float(inf), start=-float('inf')):
        self.clusters = []
        self.dirty_cluster_sort = True

        self.actives = []
        self.dirty_actives_sort = True

        self.current = start
        self.dirty_cluster_position = True

        self.valid_low_value = low_value
        self.valid_high_value = high_value
        self.cluster_range_index = 0
        self.cluster_low_value = float('inf')
        self.cluster_high_value = -float('inf')

    def add_cluster(self, path):
        self.dirty_cluster_position = True
        self.dirty_cluster_sort = True
        self.dirty_actives_sort = True
        for i in range(len(path)-1):
            p0 = path[i]
            p1 = path[i+1]
            if p0.y > p1.y:
                high = p0
                low = p1
            else:
                high = p1
                low = p0
            try:
                m = (high.y - low.y) / (high.x - low.x)
            except ZeroDivisionError:
                m = float('inf')

            b = low.y - (m * low.x)
            if self.valid_low_value > high.y:
                continue  # Cluster before range.
            if self.valid_high_value < low.y:
                continue  # Cluster after range.
            cluster = [False, i, p0, p1, high, low, m, b, path]
            if self.valid_low_value < low.y:
                self.clusters.append((low.y, cluster))
            if self.valid_high_value > high.y:
                self.clusters.append((high.y, cluster))
            if high.y >= self.current >= low.y:
                cluster[0] = True
                self.actives.append(cluster)

    def valid_range(self):
        return self.valid_high_value >= self.current >= self.valid_low_value

    def next_intercept(self, delta):
        self.scanline(self.current + delta)
        self.sort_actives()
        return self.valid_range()

    def sort_clusters(self):
        if not self.dirty_cluster_sort:
            return
        self.clusters.sort(key=lambda e: e[0])
        self.dirty_cluster_sort = False

    def sort_actives(self):
        if not self.dirty_actives_sort:
            return
        self.actives.sort(key=self.intercept)
        self.dirty_actives_sort = False

    def intercept(self, e, y=None):
        if y is None:
            y = self.current
        m = e[6]
        b = e[7]
        if m == float('nan') or m == float('inf'):
            low = e[5]
            return low.x
        return (y - b) / m

    def find_cluster_position(self):
        if not self.dirty_cluster_position:
            return
        self.dirty_cluster_position = False
        self.sort_clusters()

        self.cluster_range_index = -1
        self.cluster_high_value = -float('inf')
        self.increment_cluster()

        while self.is_higher_than_cluster_range(self.current):
            self.increment_cluster()

    def in_cluster_range(self, v):
        return not self.is_lower_than_cluster_range(v) and not self.is_higher_than_cluster_range(v)

    def is_lower_than_cluster_range(self, v):
        return v < self.cluster_low_value

    def is_higher_than_cluster_range(self, v):
        return v > self.cluster_high_value

    def increment_cluster(self):
        self.cluster_range_index += 1
        self.cluster_low_value = self.cluster_high_value
        if self.cluster_range_index < len(self.clusters):
            self.cluster_high_value = self.clusters[self.cluster_range_index][0]
        else:
            self.cluster_high_value = float('inf')
        if self.cluster_range_index > 0:
            return self.clusters[self.cluster_range_index-1][1]
        else:
            return None

    def decrement_cluster(self):
        self.cluster_range_index -= 1
        self.cluster_high_value = self.cluster_low_value
        if self.cluster_range_index > 0:
            self.cluster_low_value = self.clusters[self.cluster_range_index-1][0]
        else:
            self.cluster_low_value = -float('inf')
        return self.clusters[self.cluster_range_index][1]

    def is_point_inside(self, x, y):
        self.scanline(y)
        self.sort_actives()
        for i in range(1, len(self.actives), 2):
            prior = self.actives[i-1]
            after = self.actives[i]
            if self.intercept(prior, y) <= x <= self.intercept(after, y):
                return True
        return False

    def scanline(self, scan):
        self.dirty_actives_sort = True
        self.sort_clusters()
        self.find_cluster_position()

        while self.is_lower_than_cluster_range(scan):
            c = self.decrement_cluster()
            if c[0]:
                c[0] = False
                self.actives.remove(c)
            else:
                c[0] = True
                self.actives.append(c)

        while self.is_higher_than_cluster_range(scan):
            c = self.increment_cluster()
            if c[0]:
                c[0] = False
                self.actives.remove(c)
            else:
                c[0] = True
                self.actives.append(c)

        self.current = scan
