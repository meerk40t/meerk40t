"""
Mixin functions for nodes.
"""

from meerk40t.core.cutcode.cubiccut import CubicCut
from meerk40t.core.cutcode.cutgroup import CutGroup
from meerk40t.core.cutcode.linecut import LineCut
from meerk40t.core.cutcode.quadcut import QuadCut
from meerk40t.svgelements import Close, CubicBezier, Line, Move, Path, QuadraticBezier


def path_to_cutobjects(
    path, settings, closed_distance=15, passes=1, original_op=None, color=None
):
    for subpath in path.as_subpaths():
        sp = Path(subpath)
        if len(sp) == 0:
            continue
        closed = (
            isinstance(sp[-1], Close)
            or abs(sp.z_point - sp.current_point) <= closed_distance
        )
        group = CutGroup(
            None,
            closed=closed,
            settings=settings,
            passes=passes,
            color=color,
        )
        group.path = sp
        group.original_op = original_op
        for seg in subpath:
            if isinstance(seg, Move):
                pass  # Move operations are ignored.
            elif isinstance(seg, Close):
                if seg.start != seg.end:
                    group.append(
                        LineCut(
                            seg.start,
                            seg.end,
                            settings=settings,
                            passes=passes,
                            parent=group,
                            color=color,
                        )
                    )
            elif isinstance(seg, Line):
                if seg.start != seg.end:
                    group.append(
                        LineCut(
                            seg.start,
                            seg.end,
                            settings=settings,
                            passes=passes,
                            parent=group,
                            color=color,
                        )
                    )
            elif isinstance(seg, QuadraticBezier):
                group.append(
                    QuadCut(
                        seg.start,
                        seg.control,
                        seg.end,
                        settings=settings,
                        passes=passes,
                        parent=group,
                        color=color,
                    )
                )
            elif isinstance(seg, CubicBezier):
                group.append(
                    CubicCut(
                        seg.start,
                        seg.control1,
                        seg.control2,
                        seg.end,
                        settings=settings,
                        passes=passes,
                        parent=group,
                        color=color,
                    )
                )
        if len(group) > 0:
            group[0].first = True
        for i, cut_obj in enumerate(group):
            cut_obj.closed = closed
            try:
                cut_obj.next = group[i + 1]
            except IndexError:
                cut_obj.last = True
                cut_obj.next = group[0]
            cut_obj.previous = group[i - 1]
        yield group
