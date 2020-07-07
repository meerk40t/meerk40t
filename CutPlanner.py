from svgelements import *


class CutPlanner:

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
            inner_path.bounding_box = CutPlanner.bounding_box(inner_path)
        if not hasattr(outer_path, 'bounding_box'):
            outer_path.bounding_box = CutPlanner.bounding_box(outer_path)
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
            for k in range(j + 1, len(subpaths)):
                if CutPlanner.is_inside(subpaths[k], subpaths[j]):
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

    @staticmethod
    def length_travel(paths):
        distance = 0.0
        for p in paths:
            for s in p:
                if isinstance(s, Move):
                    if s.start is not None:
                        distance += Point.distance(s.start, s.end)
        return distance

    @staticmethod
    def optimize_travel(paths):
        optimized = Path()
        if isinstance(paths, Path):
            paths = [paths]
        subpaths = []
        for path in paths:
            subpaths.extend([abs(Path(s)) for s in path.as_subpaths()])
        improved = True
        while improved:
            improved = False
            for j in range(len(subpaths)):
                for k in range(j + 1, len(subpaths)):
                    new_cut = CutPlanner.delta_distance(subpaths, j, k)
                    if new_cut < 0:
                        CutPlanner.cross(subpaths, j, k)
                        improved = True
        for p in subpaths:
            optimized += p
        return optimized

    @staticmethod
    def cross(subpaths, j, k):
        """
        Reverses subpaths flipping the individual elements from position j inclusive to
        k exclusive.
        :param subpaths:
        :param j:
        :param k:
        :return:
        """
        for q in range(j, k):
            subpaths[q].direct_close()
            subpaths[q].reverse()
        subpaths[j:k] = subpaths[j:k][::-1]

    @staticmethod
    def delta_distance(subpaths, j, k):
        distance = 0.0
        k -= 1
        a1 = subpaths[j][0].end
        b0 = subpaths[k][-1].end
        if k < len(subpaths) - 1:
            b1 = subpaths[k + 1][0].end
            d = Point.distance(b0, b1)
            distance -= d
            d = Point.distance(a1, b1)
            distance += d
        if j > 0:
            a0 = subpaths[j - 1][-1].end
            d = Point.distance(a0, a1)
            distance -= d
            d = Point.distance(a0, b0)
            distance += d
        return distance

    @staticmethod
    def distance_path(subpaths):
        distance = 0.0
        for s in range(len(subpaths) - 1):
            j = subpaths[s]
            k = subpaths[s + 1]
            d = Point.distance(j[-1].end, k[0].end)
            distance += d
        return distance

    @staticmethod
    def is_order_constrained(paths, constraints, j, k):
        """Is the order of the sequences between j and k constrained. Such that reversing this order will violate
        the constraints."""
        for q in range(j, k):
            # search between j and k.
            first_path = paths[q]
            for constraint in constraints:
                if first_path is not constraint[0]:
                    # Constraint does not apply to the value at q.
                    continue
                for m in range(q + 1, k):
                    second_path = paths[m]
                    if second_path is constraint[1]:
                        # Constraint demands the order must be first_path then second_path.
                        return True
        return False

    @staticmethod
    def optimize_general(paths):
        optimized = Path()
        if isinstance(paths, Path):
            paths = [paths]
        subpaths = []
        for path in paths:
            subpaths.extend([abs(Path(s)) for s in path.as_subpaths()])
        constraints = []
        for j in range(len(subpaths)):
            for k in range(j + 1, len(subpaths)):
                if CutPlanner.is_inside(subpaths[k], subpaths[j]):
                    constraints.append((subpaths[k], subpaths[j]))
                elif CutPlanner.is_inside(subpaths[j], subpaths[k]):
                    constraints.append((subpaths[j], subpaths[k]))
        for j in range(len(subpaths)):
            for k in range(j + 1, len(subpaths)):
                if CutPlanner.is_inside(subpaths[k], subpaths[j]):
                    t = subpaths[j]
                    subpaths[j] = subpaths[k]
                    subpaths[k] = t
        # for constraint in constraints:
        #     success = False
        #     for q in range(len(subpaths)):
        #         first_path = subpaths[q]
        #         if first_path is constraint[0]:
        #             for m in range(q, len(subpaths)):
        #                 second_path = subpaths[m]
        #                 if second_path is constraint[1]:
        #                     success = True
        improved = True
        while improved:
            improved = False
            for j in range(len(subpaths)):
                for k in range(j + 1, len(subpaths)):
                    new_cut = CutPlanner.delta_distance(subpaths, j, k)
                    if new_cut < 0:
                        if CutPlanner.is_order_constrained(subpaths, constraints, j, k):
                            # Our order is constrained. Performing 2-opt cross is disallowed.
                            continue
                        CutPlanner.cross(subpaths, j, k)
                        improved = True
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
        for i in range(len(path) - 1):
            p0 = path[i]
            p1 = path[i + 1]
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
            return self.clusters[self.cluster_range_index - 1][1]
        else:
            return None

    def decrement_cluster(self):
        self.cluster_range_index -= 1
        self.cluster_high_value = self.cluster_low_value
        if self.cluster_range_index > 0:
            self.cluster_low_value = self.clusters[self.cluster_range_index - 1][0]
        else:
            self.cluster_low_value = -float('inf')
        return self.clusters[self.cluster_range_index][1]

    def is_point_inside(self, x, y):
        self.scanline(y)
        self.sort_actives()
        for i in range(1, len(self.actives), 2):
            prior = self.actives[i - 1]
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
