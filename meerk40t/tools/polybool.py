"""
https://github.com/KaivnD/pypolybool
MIT License
"""

import typing

tolerance = 1e-10

T = typing.TypeVar("T")
TPoint = typing.TypeVar("TPoint", bound="Point")


class PolyBoolException(Exception):
    pass


class Point:
    def __init__(self: TPoint, x: float, y: float) -> None:
        self.x = x
        self.y = y

    @staticmethod
    def collinear(pt1: TPoint, pt2: TPoint, pt3: TPoint) -> bool:
        dx1 = pt1.x - pt2.x
        dy1 = pt1.y - pt2.y
        dx2 = pt2.x - pt3.x
        dy2 = pt2.y - pt3.y
        return abs(dx1 * dy2 - dx2 * dy1) < tolerance

    @staticmethod
    def compare(pt1: TPoint, pt2: TPoint):
        if abs(pt1.x - pt2.x) < tolerance:
            return 0 if abs(pt1.y - pt2.y) < tolerance else -1 if pt1.y < pt2.y else 1
        return -1 if pt1.x < pt2.x else 1

    @staticmethod
    def pointAboveOrOnLine(point: TPoint, left: TPoint, right: TPoint):
        return (right.x - left.x) * (point.y - left.y) - (right.y - left.y) * (
            point.x - left.x
        ) >= -tolerance

    @staticmethod
    def between(point: TPoint, left: TPoint, right: TPoint):
        dPyLy = point.y - left.y
        dRxLx = right.x - left.x
        dPxLx = point.x - left.x
        dRyLy = right.y - left.y

        dot = dPxLx * dRxLx + dPyLy * dRyLy
        if dot < tolerance:
            return False

        sqlen = dRxLx * dRxLx + dRyLy * dRyLy
        if dot - sqlen > -tolerance:
            return False

        return True

    @staticmethod
    def linesIntersect(a0: TPoint, a1: TPoint, b0: TPoint, b1: TPoint):
        adx = a1.x - a0.x
        ady = a1.y - a0.y
        bdx = b1.x - b0.x
        bdy = b1.y - b0.y

        axb = adx * bdy - ady * bdx

        if abs(axb) < tolerance:
            return None

        dx = a0.x - b0.x
        dy = a0.y - b0.y

        a = (bdx * dy - bdy * dx) / axb
        b = (adx * dy - ady * dx) / axb

        return IntersectionPoint(
            Point.__calcAlongUsingValue(a),
            Point.__calcAlongUsingValue(b),
            Point(a0.x + a * adx, a0.y + a * ady),
        )

    @staticmethod
    def __calcAlongUsingValue(value: float):
        if value <= -tolerance:
            return -2
        elif value < tolerance:
            return -1
        elif value - 1 <= -tolerance:
            return 0
        elif value - 1 < tolerance:
            return 1
        else:
            return 2

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Point):
            return False
        return abs(self.x - __o.x) < tolerance and abs(self.y - __o.y) < tolerance

    def __repr__(self) -> str:
        return f"{self.x},{self.y}"

    def __str__(self) -> str:
        return f"{self.x},{self.y}"


class Fill:
    def __init__(self, below: bool = None, above: bool = None) -> None:
        self.below = below
        self.above = above

    def __repr__(self) -> str:
        return f"{self.above},{self.below}"

    def __str__(self) -> str:
        return f"{self.above},{self.below}"


class Segment:
    def __init__(
        self, start: Point, end: Point, myfill: Fill = None, otherfill: Fill = None
    ):
        self.start = start
        self.end = end
        self.myfill = myfill
        self.otherfill = otherfill

    def __repr__(self) -> str:
        return f"S: {self.start}, E: {self.end}"

    def __str__(self) -> str:
        return f"S: {self.start}, E: {self.end}"


class PolySegments:
    def __init__(
        self, segments: typing.List[Segment] = None, isInverted: bool = False
    ) -> None:
        self.segments = segments
        self.isInverted = isInverted


class CombinedPolySegments:
    def __init__(
        self,
        combined: typing.List[Segment] = None,
        isInverted1: bool = False,
        isInverted2: bool = False,
    ) -> None:
        self.combined = combined
        self.isInverted1 = isInverted1
        self.isInverted2 = isInverted2


class Matcher:
    def __init__(
        self,
        index: int,
        matchesHead: bool,
        matchesPt1: bool,
    ) -> None:
        self.index = index
        self.matchesHead = matchesHead
        self.matchesPt1 = matchesPt1


class IntersectionPoint:
    def __init__(self, alongA: int, alongB: int, pt: Point) -> None:
        self.alongA = alongA
        self.alongB = alongB
        self.pt = pt


TNode = typing.TypeVar("TNode", bound="Node")


class Node:
    def __init__(
        self: TNode,
        isRoot: bool = False,
        isStart: bool = False,
        pt: Point = None,
        seg: Segment = None,
        primary: bool = False,
        next: TNode = None,
        previous: TNode = None,
        other: TNode = None,
        ev: TNode = None,
        status: TNode = None,
        remove: typing.Callable = None,
    ):
        self.status = status
        self.other = other
        self.ev = ev
        self.previous = previous
        self.next = next
        self.isRoot = isRoot
        self.remove = remove
        self.isStart = isStart
        self.pt = pt
        self.seg = seg
        self.primary = primary


class Transition:
    def __init__(
        self, after: Node, before: Node, insert: typing.Callable[[Node], Node]
    ) -> None:
        self.after = after
        self.before = before
        self.insert = insert


class LinkedList:
    def __init__(self) -> None:
        self.__root = Node(isRoot=True)

    def exists(self, node: Node):
        if node is None or node is self.__root:
            return False
        return True

    def isEmpty(self):
        return self.__root.next is None

    def getHead(self):
        return self.__root.next

    def insertBefore(self, node: Node, check: typing.Callable[[Node], bool]):
        last = self.__root
        here = self.__root.next

        while here is not None:
            if check(here):
                node.previous = here.previous
                node.next = here
                here.previous.next = node
                here.previous = node
                return
            last = here
            here = here.next
        last.next = node
        node.previous = last
        node.next = None

    def findTransition(self, check: typing.Callable[[Node], bool]):
        previous = self.__root
        here = self.__root.next

        while here is not None:
            if check(here):
                break
            previous = here
            here = here.next

        def insert_func(node: Node):
            node.previous = previous
            node.next = here
            previous.next = node
            if here is not None:
                here.previous = node
            return node

        return Transition(
            before=(None if previous is self.__root else previous),
            after=here,
            insert=insert_func,
        )

    @staticmethod
    def node(data: Node):
        data.previous = None
        data.next = None

        def remove_func():
            data.previous.next = data.next
            if data.next is not None:
                data.next.previous = data.previous
            data.previous = None
            data.next = None

        data.remove = remove_func
        return data


RegionInput = typing.Union[typing.List[Point], typing.List[typing.Tuple[float, float]]]
Region = typing.List[Point]


class Polygon:
    def __init__(self, regions: typing.List[RegionInput], isInverted=False) -> None:
        _regions: typing.List[Region] = []
        for region in regions:
            tmp: Region = []
            for pt in region:
                if isinstance(pt, Point):
                    tmp.append(pt)
                elif isinstance(pt, tuple):
                    x, y = pt
                    tmp.append(Point(x, y))
            _regions.append(tmp)

        self.regions = _regions
        self.isInverted = isInverted


class Intersecter:
    def __init__(self, selfIntersection: bool) -> None:
        self.selfIntersection = selfIntersection
        self.__eventRoot = LinkedList()

    def newsegment(self, start: Point, end: Point):
        return Segment(start=start, end=end, myfill=Fill())

    def segmentCopy(self, start: Point, end: Point, seg: Segment):
        return Segment(
            start=start, end=end, myfill=Fill(seg.myfill.below, seg.myfill.above)
        )

    def __eventCompare(
        self,
        p1IsStart: bool,
        p11: Point,
        p12: Point,
        p2IsStart: bool,
        p21: Point,
        p22: Point,
    ):
        comp = Point.compare(p11, p21)
        if comp != 0:
            return comp

        if p12 == p22:
            return 0

        if p1IsStart != p2IsStart:
            return 1 if p1IsStart else -1

        return (
            1
            if Point.pointAboveOrOnLine(
                p12, p21 if p2IsStart else p22, p22 if p2IsStart else p21
            )
            else -1
        )

    def __eventAdd(self, ev: Node, otherPt: Point):
        def check_func(here: Node):
            comp = self.__eventCompare(
                ev.isStart, ev.pt, otherPt, here.isStart, here.pt, here.other.pt
            )
            return comp < 0

        self.__eventRoot.insertBefore(ev, check_func)

    def __eventAddSegmentStart(self, segment: Segment, primary: bool):
        evStart = LinkedList.node(
            Node(
                isStart=True,
                pt=segment.start,
                seg=segment,
                primary=primary,
            )
        )
        self.__eventAdd(evStart, segment.end)
        return evStart

    def __eventAddSegmentEnd(self, evStart: Node, segment: Segment, primary: bool):
        evEnd = LinkedList.node(
            Node(
                isStart=False,
                pt=segment.end,
                seg=segment,
                primary=primary,
                other=evStart,
            )
        )
        evStart.other = evEnd
        self.__eventAdd(evEnd, evStart.pt)

    def eventAddSegment(self, segment: Segment, primary: bool):
        evStart = self.__eventAddSegmentStart(segment, primary)
        self.__eventAddSegmentEnd(evStart, segment, primary)
        return evStart

    def __eventUpdateEnd(self, ev: Node, end: Point):
        ev.other.remove()
        ev.seg.end = end
        ev.other.pt = end
        self.__eventAdd(ev.other, ev.pt)

    def __eventDivide(self, ev: Node, pt: Point):
        ns = self.segmentCopy(pt, ev.seg.end, ev.seg)
        self.__eventUpdateEnd(ev, pt)
        return self.eventAddSegment(ns, ev.primary)

    def __statusCompare(self, ev1: Node, ev2: Node):
        a1 = ev1.seg.start
        a2 = ev1.seg.end
        b1 = ev2.seg.start
        b2 = ev2.seg.end

        if Point.collinear(a1, b1, b2):
            if Point.collinear(a2, b1, b2):
                return 1
            return 1 if Point.pointAboveOrOnLine(a2, b1, b2) else -1
        return 1 if Point.pointAboveOrOnLine(a1, b1, b2) else -1

    def __statusFindSurrounding(self, statusRoot: LinkedList, ev: Node):
        def check_func(here: Node):
            return self.__statusCompare(ev, here.ev) > 0

        return statusRoot.findTransition(check_func)

    def __checkIntersection(self, ev1: Node, ev2: Node):
        seg1 = ev1.seg
        seg2 = ev2.seg
        a1 = seg1.start
        a2 = seg1.end
        b1 = seg2.start
        b2 = seg2.end

        i = Point.linesIntersect(a1, a2, b1, b2)
        if i is None:
            if not Point.collinear(a1, a2, b1):
                return None
            if a1 == b2 or a2 == b1:
                return None
            a1EquB1 = a1 == b1
            a2EquB2 = a2 == b2
            if a1EquB1 and a2EquB2:
                return ev2

            a1Between = not a1EquB1 and Point.between(a1, b1, b2)
            a2Between = not a2EquB2 and Point.between(a2, b1, b2)

            if a1EquB1:
                if a2Between:
                    self.__eventDivide(ev2, a2)
                else:
                    self.__eventDivide(ev1, b2)

                return ev2
            elif a1Between:
                if not a2EquB2:
                    if a2Between:
                        self.__eventDivide(ev2, a2)
                    else:
                        self.__eventDivide(ev1, b2)
                self.__eventDivide(ev2, a1)
        else:
            if i.alongA == 0:
                if i.alongB == -1:
                    self.__eventDivide(ev1, b1)
                elif i.alongB == 0:
                    self.__eventDivide(ev1, i.pt)
                elif i.alongB == 1:
                    self.__eventDivide(ev1, b2)
            if i.alongB == 0:
                if i.alongA == -1:
                    self.__eventDivide(ev2, a1)
                elif i.alongA == 0:
                    self.__eventDivide(ev2, i.pt)
                elif i.alongA == 1:
                    self.__eventDivide(ev2, a2)
        return None

    def __checkBothIntersections(self, above: Node, ev: Node, below: Node):
        if above is not None:
            eve = self.__checkIntersection(ev, above)
            if eve is not None:
                return eve
        if below is not None:
            return self.__checkIntersection(ev, below)

        return None

    def calculate(self, primaryPolyInverted: bool, secondaryPolyInverted: bool):
        statusRoot = LinkedList()
        segments: typing.List[Segment] = []

        cnt = 0

        while not self.__eventRoot.isEmpty():
            cnt += 1
            ev = self.__eventRoot.getHead()
            if ev.isStart:
                surrounding = self.__statusFindSurrounding(statusRoot, ev)
                above = (
                    surrounding.before.ev if surrounding.before is not None else None
                )
                below = surrounding.after.ev if surrounding.after is not None else None

                eve = self.__checkBothIntersections(above, ev, below)
                if eve is not None:
                    if self.selfIntersection:
                        toggle = False
                        if ev.seg.myfill.below is None:
                            toggle = True
                        else:
                            toggle = ev.seg.myfill.above != ev.seg.myfill.below

                        if toggle:
                            eve.seg.myfill.above = not eve.seg.myfill.above
                    else:
                        eve.seg.otherfill = ev.seg.myfill
                    ev.other.remove()
                    ev.remove()

                if self.__eventRoot.getHead() is not ev:
                    continue

                if self.selfIntersection:
                    toggle = False
                    if ev.seg.myfill.below is None:
                        toggle = True
                    else:
                        toggle = ev.seg.myfill.above != ev.seg.myfill.below

                    if below is None:
                        ev.seg.myfill.below = primaryPolyInverted
                    else:
                        ev.seg.myfill.below = below.seg.myfill.above

                    if toggle:
                        ev.seg.myfill.above = not ev.seg.myfill.below
                    else:
                        ev.seg.myfill.above = ev.seg.myfill.below
                else:
                    if ev.seg.otherfill is None:
                        inside = False
                        if below is None:
                            inside = (
                                secondaryPolyInverted
                                if ev.primary
                                else primaryPolyInverted
                            )
                        else:
                            if ev.primary == below.primary:
                                inside = below.seg.otherfill.above
                            else:
                                inside = below.seg.myfill.above
                        ev.seg.otherfill = Fill(inside, inside)
                ev.other.status = surrounding.insert(LinkedList.node(Node(ev=ev)))
            else:
                st = ev.status
                if st is None:
                    raise PolyBoolException(
                        "PolyBool: Zero-length segment detected; your epsilon is probably too small or too large"
                    )
                if statusRoot.exists(st.previous) and statusRoot.exists(st.next):
                    self.__checkIntersection(st.previous.ev, st.next.ev)
                st.remove()

                if not ev.primary:
                    s = ev.seg.myfill
                    ev.seg.myfill = ev.seg.otherfill
                    ev.seg.otherfill = s
                segments.append(ev.seg)
            self.__eventRoot.getHead().remove()
        return segments


class RegionIntersecter(Intersecter):
    def __init__(self) -> None:
        super().__init__(True)

    def addRegion(self, region: Region):
        pt1: Point
        pt2 = region[-1]
        for i in range(len(region)):
            pt1 = pt2
            pt2 = region[i]
            forward = Point.compare(pt1, pt2)

            if forward == 0:
                continue

            seg = self.newsegment(
                pt1 if forward < 0 else pt2, pt2 if forward < 0 else pt1
            )

            self.eventAddSegment(seg, True)

    def calculate(self, inverted: bool):
        return super().calculate(inverted, False)


class SegmentIntersecter(Intersecter):
    def __init__(self) -> None:
        super().__init__(False)

    def calculate(
        self,
        segments1: typing.List[Segment],
        isInverted1: bool,
        segments2: typing.List[Segment],
        isInverted2: bool,
    ):
        for seg in segments1:
            self.eventAddSegment(self.segmentCopy(seg.start, seg.end, seg), True)

        for seg in segments2:
            self.eventAddSegment(self.segmentCopy(seg.start, seg.end, seg), False)

        return super().calculate(isInverted1, isInverted2)


class SegmentChainerMatcher:
    def __init__(self) -> None:
        self.firstMatch = Matcher(0, False, False)
        self.secondMatch = Matcher(0, False, False)

        self.nextMatch = self.firstMatch

    def setMatch(self, index: int, matchesHead: bool, matchesPt1: bool):
        self.nextMatch.index = index
        self.nextMatch.matchesHead = matchesHead
        self.nextMatch.matchesPt1 = matchesPt1
        if self.nextMatch is self.firstMatch:
            self.nextMatch = self.secondMatch
            return False
        self.nextMatch = None
        return True


def list_shift(list: typing.List):
    list.pop(0)


def list_pop(list: typing.List):
    list.pop()


def list_splice(list: typing.List, index: int, count: int):
    del list[index : index + count]


def list_unshift(list: typing.List[T], element: T):
    list.insert(0, element)


def segmentChainer(segments: typing.List[Segment]) -> typing.List[Region]:
    regions: typing.List[Region] = []
    chains: typing.List[typing.List[Point]] = []

    for seg in segments:
        pt1 = seg.start
        pt2 = seg.end
        if pt1 == pt2:
            continue

        scm = SegmentChainerMatcher()

        for i in range(len(chains)):
            chain = chains[i]
            head = chain[0]
            tail = chain[-1]

            if head == pt1:
                if scm.setMatch(i, True, True):
                    break
            elif head == pt2:
                if scm.setMatch(i, True, False):
                    break
            elif tail == pt1:
                if scm.setMatch(i, False, True):
                    break
            elif tail == pt2:
                if scm.setMatch(i, False, False):
                    break

        if scm.nextMatch is scm.firstMatch:
            chains.append([pt1, pt2])
            continue

        if scm.nextMatch is scm.secondMatch:
            index = scm.firstMatch.index
            pt = pt2 if scm.firstMatch.matchesPt1 else pt1
            addToHead = scm.firstMatch.matchesHead

            chain = chains[index]
            grow = chain[0] if addToHead else chain[-1]
            grow2 = chain[1] if addToHead else chain[-2]
            oppo = chain[-1] if addToHead else chain[0]
            oppo2 = chain[-2] if addToHead else chain[1]

            if Point.collinear(grow2, grow, pt):
                if addToHead:
                    list_shift(chain)
                else:
                    list_pop(chain)
                grow = grow2
            if oppo == pt:
                list_splice(chains, index, 1)
                if Point.collinear(oppo2, oppo, grow):
                    if addToHead:
                        list_pop(chain)
                    else:
                        list_shift(chain)
                regions.append(chain)
                continue
            if addToHead:
                list_unshift(chain, pt)
            else:
                chain.append(pt)
            continue

        def reverseChain(index: int):
            chains[index].reverse()

        def appendChain(index1: int, index2: int):
            chain1 = chains[index1]
            chain2 = chains[index2]
            tail = chain1[-1]
            tail2 = chain1[-2]
            head = chain2[0]
            head2 = chain2[1]

            if Point.collinear(tail2, tail, head):
                list_pop(chain1)
                tail = tail2
            if Point.collinear(tail, head, head2):
                list_shift(chain2)

            chains[index1] = chain1 + chain2
            list_splice(chains, index2, 1)

        f = scm.firstMatch.index
        s = scm.secondMatch.index

        reverseF = len(chains[f]) < len(chains[s])
        if scm.firstMatch.matchesHead:
            if scm.secondMatch.matchesHead:
                if reverseF:
                    reverseChain(f)
                    appendChain(f, s)
                else:
                    reverseChain(s)
                    appendChain(s, f)
            else:
                appendChain(s, f)
        else:
            if scm.secondMatch.matchesHead:
                appendChain(f, s)
            else:
                if reverseF:
                    reverseChain(f)
                    appendChain(s, f)
                else:
                    reverseChain(s)
                    appendChain(f, s)

    return regions


def __select(segments: typing.List[Segment], selection: typing.List[int]):
    result: typing.List[Segment] = []
    for seg in segments:
        index = (
            (8 if seg.myfill.above else 0)
            + (4 if seg.myfill.below else 0)
            + (2 if seg.otherfill is not None and seg.otherfill.above else 0)
            + (1 if seg.otherfill is not None and seg.otherfill.below else 0)
        )

        if selection[index] != 0:
            result.append(
                Segment(
                    start=seg.start,
                    end=seg.end,
                    myfill=Fill(selection[index] == 2, above=selection[index] == 1),
                )
            )
    return result


# core API
def segments(poly: Polygon) -> PolySegments:
    i = RegionIntersecter()
    for region in poly.regions:
        i.addRegion(region)
    return PolySegments(i.calculate(poly.isInverted), poly.isInverted)


def combine(segments1: PolySegments, segments2: PolySegments) -> CombinedPolySegments:
    i = SegmentIntersecter()
    return CombinedPolySegments(
        i.calculate(
            segments1.segments,
            segments1.isInverted,
            segments2.segments,
            segments2.isInverted,
        ),
        segments1.isInverted,
        segments2.isInverted,
    )


def selectUnion(polyseg: CombinedPolySegments) -> PolySegments:
    return PolySegments(
        segments=__select(
            # fmt:off
            polyseg.combined, [
                0, 2, 1, 0,
                2, 2, 0, 0,
                1, 0, 1, 0,
                0, 0, 0, 0,
            ]
            # fmt:on
        ),
        isInverted=(polyseg.isInverted1 or polyseg.isInverted2),
    )


def selectIntersect(polyseg: CombinedPolySegments) -> PolySegments:
    return PolySegments(
        segments=__select(
            # fmt:off
            polyseg.combined, [
                0, 0, 0, 0,
                0, 2, 0, 2,
                0, 0, 1, 1,
                0, 2, 1, 0
            ]
            # fmt:on
        ),
        isInverted=(polyseg.isInverted1 and polyseg.isInverted2),
    )


def selectDifference(polyseg: CombinedPolySegments) -> PolySegments:
    return PolySegments(
        segments=__select(
            # fmt:off
            polyseg.combined, [
                0, 0, 0, 0,
                2, 0, 2, 0,
                1, 1, 0, 0,
                0, 1, 2, 0
            ]
            # fmt:on
        ),
        isInverted=(polyseg.isInverted1 and not polyseg.isInverted2),
    )


def selectDifferenceRev(polyseg: CombinedPolySegments) -> PolySegments:
    return PolySegments(
        segments=__select(
            # fmt:off
            polyseg.combined, [
                0, 2, 1, 0,
                0, 0, 1, 1,
                0, 2, 0, 2,
                0, 0, 0, 0
            ]
            # fmt:on
        ),
        isInverted=(not polyseg.isInverted1 and polyseg.isInverted2),
    )


def selectXor(polyseg: CombinedPolySegments) -> PolySegments:
    return PolySegments(
        segments=__select(
            # fmt:off
            polyseg.combined, [
                0, 2, 1, 0,
                2, 0, 0, 1,
                1, 0, 0, 2,
                0, 1, 2, 0
            ]
            # fmt:on
        ),
        isInverted=(polyseg.isInverted1 != polyseg.isInverted2),
    )


def polygon(segments: PolySegments):
    return Polygon(segmentChainer(segments.segments), segments.isInverted)


def __operate(
    poly1: Polygon,
    poly2: Polygon,
    selector: typing.Callable[[CombinedPolySegments], PolySegments],
):
    firstPolygonRegions = segments(poly1)
    secondPolygonRegions = segments(poly2)
    combinedSegments = combine(firstPolygonRegions, secondPolygonRegions)
    seg = selector(combinedSegments)
    return polygon(seg)


# helper functions for common operations


@typing.overload
def union(polygons: typing.List[Polygon]) -> Polygon:
    ...


@typing.overload
def union(poly1: Polygon, poly2: Polygon) -> Polygon:
    ...


def union(*args):
    if len(args) == 1 and isinstance(args[0], list):
        polygons = args[0]
        seg1 = segments(polygons[0])
        for i in range(1, len(polygons)):
            seg2 = segments(polygons[i])
            comb = combine(seg1, seg2)
            seg1 = selectUnion(comb)

        return polygon(seg1)
    elif (
        len(args) == 2 and isinstance(args[0], Polygon) and isinstance(args[1], Polygon)
    ):
        return __operate(args[0], args[1], selectUnion)


def intersect(poly1: Polygon, poly2: Polygon):
    return __operate(poly1, poly2, selectIntersect)


def difference(poly1: Polygon, poly2: Polygon):
    return __operate(poly1, poly2, selectDifference)


def differenceRev(poly1: Polygon, poly2: Polygon):
    return __operate(poly1, poly2, selectDifferenceRev)


def xor(poly1: Polygon, poly2: Polygon):
    return __operate(poly1, poly2, selectXor)
