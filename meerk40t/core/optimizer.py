from meerk40t.svgelements import Point, Group, Polygon
from meerk40t.tools.pathtools import VectorMontonizer


class Optimizer:
    def __init__(self, cutcode):
        self.cutcode = cutcode
        self.two_opt = True
        self.two_opt_passes = 3
        self.travel = True

    def optimize(self):
        old_len = self.length_travel()
        self.optimize_travel()
        new_len = self.length_travel()
        red = new_len-old_len
        try:
            print("%f -> %f reduced %f (%f%%)" % (old_len, new_len, red, 100 * (red/old_len)))
        except ZeroDivisionError:
            pass

    def delta_distance(self, j, k):
        cutcode = self.cutcode
        a1 = cutcode[j].start()
        a0 = cutcode[j - 1].end()
        b0 = cutcode[k-1].end()
        b1 = cutcode[k].start()
        return Point.distance(a0, b0) + Point.distance(a1, b1) - Point.distance(a0, a1) - Point.distance(b0, b1)

    def optimize_travel(self):
        cutcode = self.cutcode
        improved = True
        passes = self.two_opt_passes
        while improved:
            passes -= 1
            improved = False
            for j in range(1,len(cutcode)-1):
                for k in range(j + 1, len(cutcode)):
                    new_cut = self.delta_distance(j, k)
                    if new_cut < 0:
                        self.cross(j, k)
                        improved = True
            if passes <= 0:
                break

    def optimize_cut_inside(self):
        subpaths = self.cutcode
        for j in range(len(subpaths)):
            for k in range(j + 1, len(subpaths)):
                if self.is_inside(subpaths[k], subpaths[j]):
                    t = subpaths[j]
                    subpaths[j] = subpaths[k]
                    subpaths[k] = t

    def optimize_general(self):
        subpaths = self.cutcode
        constraints = []
        for j in range(len(subpaths)):
            for k in range(j + 1, len(subpaths)):
                if self.is_inside(subpaths[k], subpaths[j]):
                    constraints.append((subpaths[k], subpaths[j]))
                elif self.is_inside(subpaths[j], subpaths[k]):
                    constraints.append((subpaths[j], subpaths[k]))
        for j in range(len(subpaths)):
            for k in range(j + 1, len(subpaths)):
                if self.is_inside(subpaths[k], subpaths[j]):
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
                    new_cut = self.delta_distance(j, k)
                    if new_cut < 0:
                        if self.is_order_constrained(constraints, j, k):
                            # Our order is constrained. Performing 2-opt cross is disallowed.
                            continue
                        self.cross(j, k)
                        improved = True

    def length_travel(self):
        cutcode = self.cutcode
        distance = 0.0
        for i in range(1, len(cutcode)):
            prev = cutcode[i-1]
            curr = cutcode[i]
            distance += Point.distance(prev.end(), curr.start())
        return distance

    def cross(self, j, k):
        """
        Reverses subpaths flipping the individual elements from position j inclusive to
        k exclusive.
        :param subpaths:
        :param j:
        :param k:
        :return:
        """
        cutcode = self.cutcode
        for q in range(j, k):
            cutcode[q].reverse()
        cutcode[j:k] = cutcode[j:k][::-1]

    def is_order_constrained(self, constraints, j, k):
        """Is the order of the sequences between j and k constrained. Such that reversing this order will violate
        the constraints."""
        cutcode = self.cutcode
        for q in range(j, k):
            # search between j and k.
            first_path = cutcode[q]
            for constraint in constraints:
                if first_path is not constraint[0]:
                    # Constraint does not apply to the value at q.
                    continue
                for m in range(q + 1, k):
                    second_path = cutcode[m]
                    if second_path is constraint[1]:
                        # Constraint demands the order must be first_path then second_path.
                        return True
        return False

    def is_inside(self, inner_path, outer_path):
        """
        Test that path1 is inside path2.
        :param inner_path: inner path
        :param outer_path: outer path
        :return: whether path1 is wholly inside path2.
        """
        if not hasattr(inner_path, "bounding_box"):
            inner_path.bounding_box = Group.union_bbox([inner_path])
        if not hasattr(outer_path, "bounding_box"):
            outer_path.bounding_box = Group.union_bbox([outer_path])
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
        if not hasattr(outer_path, "vm"):
            outer_path = Polygon(
                [outer_path.point(i / 100.0, error=1e4) for i in range(101)]
            )
            vm = VectorMontonizer()
            vm.add_cluster(outer_path)
            outer_path.vm = vm
        for i in range(101):
            p = inner_path.point(i / 100.0, error=1e4)
            if not outer_path.vm.is_point_inside(p.x, p.y):
                return False
        return True
