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
        settings=None,
        passes=1,
        constrained=False,
        closed=False,
        color=None,
        origin=None,
        skip=False,
    ):
        list.__init__(self, children)
        CutObject.__init__(
            self, parent=parent, settings=settings, passes=passes, color=color
        )
        self.closed = closed
        self.constrained = constrained
        self.burn_started = False
        self.origin = origin
        self.skip = skip

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
            yield from c.flat()

    def candidate(
        self,
        complete_path: Optional[bool] = False,
        grouped_inner: Optional[bool] = False,
    ):
        """
        Generate candidate cut objects for processing based on burns_done constraints.

        Candidates are CutObjects:
        1. That do not contain one or more unburned inner constrained cutcode objects.
        2. With Group Inner Burns, containing object is a candidate only if:
            a. It already has one containing object already burned; or
            b. There are no containing objects with at least one inner element burned.
        3. With burns done < passes (> 1 only if merge passes)
        4. With Burn Complete Paths on and non-closed subpath, only first and last segments of the subpath else all segments

        When grouped_inner=True:
        - Uses sophisticated piece-based organization
        - Creates "pieces" of related inner/outer group pairs
        - Processes complete pieces together with inner-first ordering within each piece

        When grouped_inner=False:
        - Uses hierarchical yielding with inner-first constraints
        - Processes groups individually while respecting containment hierarchy
        """
        candidates = list(self)

        if grouped_inner:
            # Implement opt_inners_grouped: "complete pieces together"
            # Group related inner/outer pairs and process complete pieces sequentially
            pieces = []  # List of pieces, where each piece is a list of related groups
            processed_groups = set()

            # Find all outer groups (groups that contain other groups)
            outer_groups = [grp for grp in candidates if grp.contains is not None]

            # For each outer group, create a piece containing the outer and its inners
            for outer in outer_groups:
                if id(outer) in processed_groups:
                    continue

                piece = [outer]  # Start piece with the outer group
                processed_groups.add(id(outer))

                # Add all inner groups that belong to this outer
                if outer.contains:
                    for inner in outer.contains:
                        if inner in candidates and id(inner) not in processed_groups:
                            piece.append(inner)
                            processed_groups.add(id(inner))

                pieces.append(piece)

            # Add any remaining groups that aren't part of inner/outer relationships
            remaining_groups = [
                grp for grp in candidates if id(grp) not in processed_groups
            ]
            for grp in remaining_groups:
                pieces.append([grp])  # Each standalone group is its own "piece"

            # Reorder candidates to process complete pieces together
            # Within each piece: inner groups first, then outer group
            candidates = []
            for piece in pieces:
                # Sort within piece: inners first (groups with .inside), then outers (groups with .contains)
                # Note: A group can be both inner AND outer (e.g., medium group), so we need to avoid duplicates
                inners = [
                    grp
                    for grp in piece
                    if grp.inside is not None and grp.contains is None
                ]
                outers = [
                    grp
                    for grp in piece
                    if grp.contains is not None and grp.inside is None
                ]
                both = [
                    grp
                    for grp in piece
                    if grp.inside is not None and grp.contains is not None
                ]
                others = [
                    grp for grp in piece if grp.inside is None and grp.contains is None
                ]

                # Add to candidates in order: inners, both (inner+outer), others, outers (within each piece)
                candidates.extend(inners + both + others + outers)

        # Different yielding strategies based on grouped_inner
        if grouped_inner:
            # For grouped_inner: respect the piece ordering we've established
            # Process complete pieces together: inner groups first, then outer group within each piece
            for grp in candidates:
                # Skip if already burned
                if grp.is_burned():
                    continue

                # Yield segments according to complete_path rules
                if complete_path and not grp.closed and isinstance(grp, CutGroup) and getattr(grp, 'original_op', None) not in ("op cut", "op engrave"):
                    if grp[0].burns_done < grp[0].passes:
                        yield grp[0]
                    if len(grp) > 1 and grp[-1].burns_done < grp[-1].passes:
                        yield grp[-1]
                else:
                    for seg in grp.flat():
                        if seg is not None and seg.burns_done < seg.passes:
                            yield seg
        else:
            # For non-grouped: use hierarchical yielding with inner-first constraints
            # Track which groups have been processed using their IDs
            processed_group_ids = set()
            remaining_candidates = list(candidates)

            while remaining_candidates:
                # Find groups that can be burned in this iteration
                # (no unburned inner groups OR their inners have been processed)
                ready_to_burn = []
                for grp in remaining_candidates:
                    can_burn = True
                    if hasattr(grp, "contains") and grp.contains is not None:
                        for inner in grp.contains:
                            if (
                                id(inner) not in processed_group_ids
                                and not inner.is_burned()
                            ):
                                can_burn = False
                                break
                    if can_burn:
                        ready_to_burn.append(grp)

                # If no groups are ready, break to avoid infinite loop
                if not ready_to_burn:
                    break

                # Yield segments from ready groups and mark them as processed
                for grp in ready_to_burn:
                    remaining_candidates.remove(grp)
                    processed_group_ids.add(id(grp))

                    # Yield segments according to complete_path rules
                    if complete_path and not grp.closed and isinstance(grp, CutGroup) and getattr(grp, 'original_op', None) not in ("op cut", "op engrave"):
                        if grp[0].burns_done < grp[0].passes:
                            yield grp[0]
                        if len(grp) > 1 and grp[-1].burns_done < grp[-1].passes:
                            yield grp[-1]
                    else:
                        for seg in grp.flat():
                            if seg is not None and seg.burns_done < seg.passes:
                                yield seg

            # If any groups remain, yield them anyway to ensure no cutcode is lost
            for grp in remaining_candidates:
                if complete_path and not grp.closed and isinstance(grp, CutGroup) and getattr(grp, 'original_op', None) not in ("op cut", "op engrave"):
                    if grp[0].burns_done < grp[0].passes:
                        yield grp[0]
                    if len(grp) > 1 and grp[-1].burns_done < grp[-1].passes:
                        yield grp[-1]
                else:
                    for seg in grp.flat():
                        if seg is not None and seg.burns_done < seg.passes:
                            yield seg
