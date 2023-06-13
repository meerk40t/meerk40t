"""Common methods for grouping overlapping raster elements.

Currently used:

*   During 2-pass classification to ensure that overlapping raster elements
    are classified to the same Raster operation(s)

*   When creating images from rasters during planning to avoid creating a single huge raster
    and optimise raster time by avoiding sweeping large empty areas.
"""

from typing import Any, Sequence, Tuple, Union

from ..core.cutcode import RasterCut
from ..svgelements import SVGElement


def group_overlapped_rasters(
    group: Sequence[Tuple[Any, Tuple]],
) -> (Sequence[Sequence[Tuple[Any, Tuple]]]):
    """
    A group consists of a list of elements and associated bboxes.

    This method takes a single group and breaks it into separate groups which are not overlapping
    by breaking into a list of groups each containing a single element and then combining them
    when any element in one group overlaps with any element in another.

    returns: list of groups
    """
    groups = [[x] for x in group]
    # print("initial", list(map(lambda g: list(map(lambda e: e[0].id,g)), groups)))

    # We are using old fashioned iterators because Python cannot cope with consolidating a list whilst iterating over it.
    for i in range(len(groups) - 2, -1, -1):
        g1 = groups[i]
        if g1 is None:
            continue
        for j in range(len(groups) - 1, i, -1):
            g2 = groups[j]
            if g2 is None:
                continue
            if group_elements_overlap(g1, g2):
                # print("g1", list(map(lambda e: e[0].id,g1)))
                # print("g2", list(map(lambda e: e[0].id,g2)))

                # if elements in the group overlap
                # add the element tuples from group 2 to group 1
                g1.extend(g2)
                # and remove group 2
                del groups[j]

                # print("g1+g2", list(map(lambda e: e[0].id,g1)))
                # print("reduced", list(map(lambda g: list(map(lambda e: e[0].id,g)), raster_groups)))
    return groups


def group_elements_overlap(
    g1: Tuple[Union[SVGElement, RasterCut], Tuple],
    g2: Tuple[Union[SVGElement, RasterCut], Tuple],
) -> bool:
    for e1 in g1:
        if e1 is None:
            return False
        e1xmin, e1ymin, e1xmax, e1ymax = e1[1]
        for e2 in g2:
            if e1 is None:
                return False
            e2xmin, e2ymin, e2xmax, e2ymax = e2[1]
            if (
                e1xmin <= e2xmax
                and e1xmax >= e2xmin
                and e1ymin <= e2ymax
                and e1ymax >= e2ymin
            ):
                return True
    return False
