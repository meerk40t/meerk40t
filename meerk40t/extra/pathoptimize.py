from ..core.cutplan import is_inside
from ..svgelements import Move, Path, Point


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root

        @context.console_command("optimize", help=_("optimize <type>"))
        def optimize(command, channel, _, args=tuple(), **kwargs):
            elements = context.elements
            if not elements.has_emphasis():
                channel(_("No selected elements."))
                return
            elif len(args) == 0:
                channel(_("Optimizations: cut_inner, travel, cut_travel"))
                return
            elif args[0] == "cut_inner":
                for node in elements.elems(emphasized=True):
                    try:
                        path = node.path
                    except AttributeError:
                        continue
                    e = optimize_cut_inside(path)
                    path.clear()
                    path += e
                    node.altered()
            elif args[0] == "travel":
                channel(
                    _("Travel Optimizing: {length}").format(
                        length=length_travel(elements.elems(emphasized=True))
                    )
                )
                for node in elements.elems(emphasized=True):
                    try:
                        path = node.path
                    except AttributeError:
                        continue
                    e = optimize_travel(path)
                    path.clear()
                    path.path += e
                    node.altered()
                channel(
                    _("Optimized: {length}").format(
                        length=length_travel(elements.elems(emphasized=True))
                    )
                )
            elif args[0] == "cut_travel":
                channel(
                    _("Cut Travel Initial: {length}").format(
                        length=length_travel(elements.elems(emphasized=True))
                    )
                )
                for node in elements.elems(emphasized=True):
                    try:
                        path = node.path
                    except AttributeError:
                        continue
                    e = optimize_general(path)
                    path.clear()
                    path += e
                    node.altered()
                channel(
                    _("Cut Travel Optimized: {length}").format(
                        length=length_travel(elements.elems(emphasized=True))
                    )
                )
            else:
                channel(_("Optimization not found."))
                return


def optimize_cut_inside(paths):
    optimized = Path()
    if isinstance(paths, Path):
        paths = [paths]
    subpaths = []
    for path in paths:
        subpaths.extend([abs(Path(s)) for s in path.as_subpaths()])
    for j in range(len(subpaths)):
        for k in range(j + 1, len(subpaths)):
            if is_inside(subpaths[k], subpaths[j]):
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


def length_travel(paths):
    distance = 0.0
    for p in paths:
        if not isinstance(p, Path):
            continue
        for s in p:
            if isinstance(s, Move):
                if s.start is not None:
                    distance += Point.distance(s.start, s.end)
    return distance


def optimize_travel(paths):
    optimized = Path()
    if isinstance(paths, Path):
        paths = [paths]
    subpaths = []
    for path in paths:
        if not isinstance(path, Path):
            continue
        subpaths.extend([abs(Path(s)) for s in path.as_subpaths()])
    improved = True
    while improved:
        improved = False
        for j in range(len(subpaths)):
            for k in range(j + 1, len(subpaths)):
                new_cut = delta_distance(subpaths, j, k)
                if new_cut < 0:
                    cross(subpaths, j, k)
                    improved = True
    for p in subpaths:
        optimized += p
    return optimized


def cross(subpaths, j, k):
    """
    Reverses subpaths flipping the individual elements from position j inclusive to
    k exclusive.
    @param subpaths:
    @param j:
    @param k:
    @return:
    """
    for q in range(j, k):
        subpaths[q].direct_close()
        subpaths[q].reverse()
    subpaths[j:k] = subpaths[j:k][::-1]


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


def distance_path(subpaths):
    distance = 0.0
    for s in range(len(subpaths) - 1):
        j = subpaths[s]
        k = subpaths[s + 1]
        d = Point.distance(j[-1].end, k[0].end)
        distance += d
    return distance


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
            if is_inside(subpaths[k], subpaths[j]):
                constraints.append((subpaths[k], subpaths[j]))
            elif is_inside(subpaths[j], subpaths[k]):
                constraints.append((subpaths[j], subpaths[k]))
    for j in range(len(subpaths)):
        for k in range(j + 1, len(subpaths)):
            if is_inside(subpaths[k], subpaths[j]):
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
                new_cut = delta_distance(subpaths, j, k)
                if new_cut < 0:
                    if is_order_constrained(subpaths, constraints, j, k):
                        # Our order is constrained. Performing 2-opt cross is disallowed.
                        continue
                    cross(subpaths, j, k)
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
