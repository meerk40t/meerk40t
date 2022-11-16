from abc import ABC
from typing import Optional

from .cutobject import CutObject


class CutGroup(list, CutObject, ABC):
    """
    CutGroups are group container CutObject. They are used to group objects together such as
    to maintain the relationship between within a closed path object.
    """

    def __init__(
        self,
        parent,
        children=(),
        parameter_object=None,
        passes=1,
        constrained=False,
        closed=False,
    ):
        list.__init__(self, children)
        CutObject.__init__(self, parent=parent, parameter_object=parameter_object, passes=passes)
        self.closed = closed
        self.constrained = constrained
        self.burn_started = False

    def __copy__(self):
        return CutGroup(self.parent, self)

    def __str__(self):
        return f"CutGroup(children={list.__str__(self)}, parent={str(self.parent)})"

    def __repr__(self):
        return f"CutGroup(children={list.__repr__(self)}, parent={str(self.parent)})"

    def reversible(self):
        return False

    def reverse(self):
        pass

    @property
    def start(self):
        if self._start_x is not None and self._start_y is not None:
            return self._start_x, self._start_y
        if len(self) == 0:
            return None
        # handle group normal/reverse - start and end already handle segment reverse
        return self[0].start if self.normal else self[-1].end

    @property
    def end(self):
        if len(self) == 0:
            return None
        # handle group normal/reverse - start and end already handle segment reverse
        return self[-1].end if self.normal else self[0].start

    def flat(self):
        """
        Flat list of cut objects with a depth first search.
        """
        for c in self:
            if not isinstance(c, CutGroup):
                yield c
                continue
            for s in c.flat():
                yield s

    def candidate(
        self,
        complete_path: Optional[bool] = False,
        grouped_inner: Optional[bool] = False,
    ):
        """
        Candidates are CutObjects:
        1. That do not contain one or more unburned inner constrained cutcode objects.
        2. With Group Inner Burns, containing object is a candidate only if:
            a. It already has one containing object already burned; or
            b. There are no containing objects with at least one inner element burned.
        3. With burns done < passes (> 1 only if merge passes)
        4. With Burn Complete Paths on and non-closed subpath, only first and last segments of the subpath else all segments
        """
        candidates = list(self)
        if grouped_inner:
            # Create list of exactly those groups which are:
            #   a.  Unburned; and either
            #   b1. Inside an outer which has at least one inner burned; or
            #   b2. An outer which has all inner burned.
            # by removing from the list:
            #   1. Candidates already burned
            #   2. Candidates which are neither inner nor outer
            #   3. Candidates which are outer and have at least one inner not yet burned
            #   4. Candidates which are inner and all outers have no inners burned
            # If the resulting list is empty then normal rules apply instead.
            for grp in self:
                if (
                    grp.is_burned()
                    or (grp.contains is None and grp.inside is None)
                    or (grp.contains is not None and grp.contains_unburned_groups())
                ):
                    candidates.remove(grp)
                    continue
                if grp.inside is not None:
                    for outer in grp.inside:
                        if outer.contains_burned_groups():
                            break
                    else:
                        candidates.remove(grp)
            if len(candidates) == 0:
                candidates = list(self)

        for grp in candidates:
            # Do not burn this CutGroup if it contains unburned groups
            # Contains is only set when Cut Inner First is set, so this
            # so when not set this does nothing.
            if grp.contains_unburned_groups():
                continue
            # If we are only burning complete subpaths then
            # if this is not a closed path we should only yield first and last segments
            # Planner will need to determine which end of the subpath is yielded
            # and only consider the direction starting from the end
            if complete_path and not grp.closed and isinstance(grp, CutGroup):
                if grp[0].burns_done < grp[0].implicit_passes:
                    yield grp[0]
                # Do not yield same segment a 2nd time if only one segment
                if len(grp) > 1 and grp[-1].burns_done < grp[-1].implicit_passes:
                    yield grp[-1]
                continue
            # If we are either burning any path segment
            # or this is a closed path
            # then we should yield all segments.
            for seg in grp.flat():
                if seg is not None and seg.burns_done < seg.implicit_passes:
                    yield seg
