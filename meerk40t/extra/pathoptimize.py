from meerk40t.svgelements import Path, Polygon, Point, Group, Move
from meerk40t.tools.pathtools import VectorMontonizer


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        context = kernel.get_context('/')

        @context.console_command("optimize", help="optimize <type>")
        def optimize(command, channel, _, args=tuple(), **kwargs):
            elements = context.elements
            if not elements.has_emphasis():
                channel(_("No selected elements."))
                return
            elif len(args) == 0:
                channel(_("Optimizations: cut_inner, travel, cut_travel"))
                return
            elif args[0] == "cut_inner":
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_cut_inside(element)
                    element.clear()
                    element += e
                    element.node.altered()
            elif args[0] == "travel":
                channel(
                    _("Travel Optimizing: %f")
                    % CutPlanner.length_travel(elements.elems(emphasized=True))
                )
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_travel(element)
                    element.clear()
                    element += e
                    element.node.altered()
                channel(
                    _("Optimized: %f")
                    % CutPlanner.length_travel(elements.elems(emphasized=True))
                )
            elif args[0] == "cut_travel":
                channel(
                    _("Cut Travel Initial: %f")
                    % CutPlanner.length_travel(elements.elems(emphasized=True))
                )
                for element in elements.elems(emphasized=True):
                    e = CutPlanner.optimize_general(element)
                    element.clear()
                    element += e
                    element.node.altered()
                channel(
                    _("Cut Travel Optimized: %f")
                    % CutPlanner.length_travel(elements.elems(emphasized=True))
                )
            else:
                channel(_("Optimization not found."))
                return


class CutPlanner:

    @staticmethod
    def is_inside(inner_path, outer_path):
        """
        Test that path1 is inside path2.
        :param inner_path: inner path
        :param outer_path: outer path
        :return: whether path1 is wholely inside path2.
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

