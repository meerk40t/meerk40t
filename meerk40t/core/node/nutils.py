"""
Mixin functions for nodes.
"""

from meerk40t.core.cutcode.cubiccut import CubicCut
from meerk40t.core.cutcode.cutgroup import CutGroup
from meerk40t.core.cutcode.linecut import LineCut
from meerk40t.core.cutcode.quadcut import QuadCut
from meerk40t.svgelements import Close, CubicBezier, Line, Move, Path, QuadraticBezier
from meerk40t.tools.geomstr import Geomstr

def path_to_cutobjects(
    path,
    settings,
    closed_distance=15,
    passes=1,
    original_op=None,
    color=None,
    kerf=0,
    offset_routine=None,
    origin=None,
):
    source = path
    if kerf != 0 and offset_routine is not None:
        source = offset_routine(
            abs(path),
            kerf,
        )
        # source.validate_connections()
        # source.approximate_arcs_with_cubics()
        # Just a test to see if it works, replace path by it bounding box
        # bb = sp.bbox(transformed=True)
        # sp = Path(Rect(x=bb[0], y=bb[1], width=bb[2] - bb[0], height=bb[3] - bb[1]))
    for subpath in source.as_subpaths():
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
            origin=origin,
        )
        group.path = sp
        group._geometry = Geomstr.svg(sp.d())
        group.original_op = original_op
        for seg in sp:
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
        if len(group) == 0:
            # Singleton Move or something. No cutobjects in generated group.
            continue
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
