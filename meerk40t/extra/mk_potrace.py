import math
from typing import Optional, Tuple, Union

import numpy as np

try:
    from numba import njit
except ImportError:

    def njit(*args, **kwargs):
        return lambda f: f


POTRACE_TURNPOLICY_BLACK = 0
POTRACE_TURNPOLICY_WHITE = 1
POTRACE_TURNPOLICY_LEFT = 2
POTRACE_TURNPOLICY_RIGHT = 3
POTRACE_TURNPOLICY_MINORITY = 4
POTRACE_TURNPOLICY_MAJORITY = 5
POTRACE_TURNPOLICY_RANDOM = 6

# /* segment tags */
POTRACE_CURVETO = 1
POTRACE_CORNER = 2

INFTY = float("inf")
COS179 = math.cos(math.radians(179))


class Bitmap:
    def __init__(self, data, blacklevel=0.5):
        if hasattr(data, "dtype"):
            if data.dtype != "bool":
                data = data > (255 * blacklevel)
        if hasattr(data, "mode"):
            if data.mode != "L":
                data = data.convert("L")
            data = data.point(lambda e: 0 if (e / 255.0) < blacklevel else 255)
            image = data.convert("1")
            data = np.array(image)
        self.data = data
        self.invert()

    def invert(self):
        self.data = np.invert(self.data)

    def trace(
        self,
        turdsize: int = 2,
        turnpolicy: int = POTRACE_TURNPOLICY_MINORITY,
        alphamax=1.0,
        opticurve=True,
        opttolerance=0.2,
    ):
        bm = np.pad(self.data, [(0, 1), (0, 1)], mode="constant")

        plist = bm_to_pathlist(bm, turdsize=turdsize, turnpolicy=turnpolicy)
        process_path(
            plist,
            alphamax=alphamax,
            opticurve=opticurve,
            opttolerance=opttolerance,
        )
        return Path(plist)


class Path(list):
    def __init__(self, plist):
        list.__init__(self)
        self.extend([Curve(p) for p in plist])

    @property
    def curves(self):
        return self

    @property
    def curves_tree(self):
        """
        Curves tree is currently non-implemented.
        :return:
        """
        return None


class Curve(list):
    def __init__(self, p):
        list.__init__(self)
        last = None
        self._path = p
        self._curve = p._fcurve
        for s in self._curve:
            if s.tag == POTRACE_CORNER:
                self.append(CornerSegment(s))
            else:
                self.append(BezierSegment(s))
            last = s
        self.start_point = last.c[2] if last is not None else None

    @property
    def decomposition_points(self):
        return self._path.pt

    @property
    def segments(self):
        return self

    @property
    def children(self):
        """
        Curves tree is non-implemented.
        :return:
        """
        return None


class CornerSegment:
    def __init__(self, s):
        self._segment = s

    @property
    def c(self):
        return self._segment.c[1]

    @property
    def end_point(self):
        return self._segment.c[2]

    @property
    def is_corner(self):
        return True


class BezierSegment:
    def __init__(self, s):
        self._segment = s

    @property
    def c1(self):
        return self._segment.c[0]

    @property
    def c2(self):
        return self._segment.c[1]

    @property
    def end_point(self):
        return self._segment.c[2]

    @property
    def is_corner(self):
        return False


# /* ---------------------------------------------------------------------- */


class _Curve:
    def __init__(self, m):
        self.segments = [_Segment() for _ in range(m)]
        self.alphacurve = False

    def __len__(self):
        return len(self.segments)

    @property
    def n(self):
        return len(self)

    def __getitem__(self, item):
        return self.segments[item]


class _Path:
    def __init__(self, pt: list, area: int, sign: bool):
        self.pt = pt  # /* pt[len]: path as extracted from bitmap */

        self.area = area
        self.sign = sign
        self.next = None
        self.childlist = []
        self.sibling = []

        self._lon = []  # /* lon[len]: (i,lon[i]) = longest straight line from i */

        self._x0 = 0  # /* origin for sums */
        self._y0 = 0  # /* origin for sums */
        self._sums = []  # / *sums[len + 1]: cache for fast summing * /

        self._m = 0  # /* length of optimal polygon */
        self._po = []  # /* po[m]: optimal polygon */
        self._curve = []  # /* curve[m]: array of curve elements */
        self._ocurve = []  # /* ocurve[om]: array of curve elements */
        self._fcurve = []  # /* final curve: this points to either curve or ocurve.*/

    def __len__(self):
        return len(self.pt)

    def init_curve(self, m):
        pass


class _Point:
    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y

    def __repr__(self):
        return "Point(%f, %f)" % (self.x, self.y)


class _Segment:
    def __init__(self):
        self.tag = 0
        self.c = [_Point(), _Point(), _Point()]
        self.vertex = _Point()
        self.alpha = 0.0
        self.alpha0 = 0.0
        self.beta = 0.0


class _Sums:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.x2 = 0
        self.xy = 0
        self.y2 = 0


detrand_t = (
    # /* non-linear sequence: constant term of inverse in GF(8),
    #   mod x^8+x^4+x^3+x+1 */
    0,
    1,
    1,
    0,
    1,
    0,
    1,
    1,
    0,
    1,
    1,
    0,
    0,
    1,
    1,
    1,
    0,
    0,
    0,
    1,
    1,
    1,
    0,
    1,
    0,
    1,
    1,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    1,
    1,
    0,
    1,
    1,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    1,
    1,
    0,
    0,
    0,
    1,
    0,
    1,
    1,
    1,
    1,
    1,
    1,
    0,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    0,
    1,
    1,
    0,
    1,
    1,
    1,
    1,
    0,
    1,
    0,
    0,
    0,
    1,
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
    1,
    0,
    0,
    1,
    1,
    1,
    0,
    0,
    1,
    0,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    0,
    1,
    0,
    0,
    1,
    0,
    1,
    1,
    1,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    0,
    1,
    1,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
    1,
    1,
    1,
    0,
    1,
    1,
    0,
    0,
    1,
    1,
    0,
    0,
    1,
    1,
    0,
    1,
    1,
    0,
    0,
    0,
    1,
    1,
    1,
    1,
    0,
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
    1,
    1,
    0,
    0,
    0,
    1,
    0,
    1,
    1,
    0,
    0,
    1,
    1,
    1,
    0,
    1,
    0,
    0,
    1,
    1,
    0,
    0,
    1,
    1,
    1,
    0,
    0,
    1,
    1,
    1,
    0,
    0,
    0,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
    1,
    0,
)


def detrand(x: int, y: int) -> int:
    """deterministically and efficiently hash (x,y) into a pseudo-random bit"""
    # /* 0x04b3e375 and 0x05a8ef93 are chosen to contain every possible 5-bit sequence */
    z = ((0x04B3E375 * x) ^ y) * 0x05A8EF93
    z = (
        detrand_t[z & 0xFF]
        ^ detrand_t[(z >> 8) & 0xFF]
        ^ detrand_t[(z >> 16) & 0xFF]
        ^ detrand_t[(z >> 24) & 0xFF]
    )
    return z


def majority(bm: np.array, x: int, y: int) -> int:
    """
     /* return the "majority" value of bitmap bm at intersection (x,y). We
    assume that the bitmap is balanced at "radius" 1.  */
    """
    for i in range(2, 5):  # /* check at "radius" i */
        ct = 0
        for a in range(-i + 1, i - 2):
            try:
                ct += 1 if bm[y + i - 1][x + a] else -1
            except IndexError:
                pass
            try:
                ct += 1 if bm[y + a - 1][x + i - 1] else -1
            except IndexError:
                pass
            try:
                ct += 1 if bm[y - i][x + a - 1] else -1
            except IndexError:
                pass
            try:
                ct += 1 if bm[y + a][x - i] else -1
            except IndexError:
                pass
        if ct > 0:
            return 1
        elif ct < 0:
            return 0
    return 0


"""
/* ---------------------------------------------------------------------- */
/* decompose image into paths */
"""


def xor_to_ref(bm: np.array, x: int, y: int, xa: int) -> None:
    """
     /* efficiently invert bits [x,infty) and [xa,infty) in line y. Here xa
    must be a multiple of BM_WORDBITS. */
    """

    if x < xa:
        bm[y, x:xa] ^= True
    elif x != xa:
        bm[y, xa:x] ^= True


def xor_path(bm: np.array, p: _Path) -> None:
    """
    a path is represented as an array of points, which are thought to
    lie on the corners of pixels (not on their centers). The path point
    (x,y) is the lower left corner of the pixel (x,y). Paths are
    represented by the len/pt components of a path_t object (which
    also stores other information about the path) */

    xor the given pixmap with the interior of the given path. Note: the
    path must be within the dimensions of the pixmap.
    """
    if len(p) <= 0:  # /* a path of length 0 is silly, but legal */
        return

    y1 = p.pt[-1].y
    xa = p.pt[0].x
    for n in p.pt:
        x, y = n.x, n.y
        if y != y1:
            # /* efficiently invert the rectangle [x,xa] x [y,y1] */
            xor_to_ref(bm, x, min(y, y1), xa)
            y1 = y


def findpath(bm: np.array, x0: int, y0: int, sign: bool, turnpolicy: int) -> _Path:
    """
    /* compute a path in the given pixmap, separating black from white.
    Start path at the point (x0,x1), which must be an upper left corner
    of the path. Also compute the area enclosed by the path. Return a
    new path_t object, or NULL on error (note that a legitimate path
    cannot have length 0). Sign is required for correct interpretation
    of turnpolicies. */"""

    x = x0
    y = y0
    dirx = 0
    diry = -1  # diry-1
    pt = []
    area = 0

    while True:  # /* while this path */
        # /* add point to path */
        pt.append(_Point(int(x), int(y)))

        # /* move to next point */
        x += dirx
        y += diry
        area += x * diry

        # /* path complete? */
        if x == x0 and y == y0:
            break

        # /* determine next direction */
        cy = y + (diry - dirx - 1) // 2
        cx = x + (dirx + diry - 1) // 2
        try:
            c = bm[cy][cx]
        except IndexError:
            c = 0
        dy = y + (diry + dirx - 1) // 2
        dx = x + (dirx - diry - 1) // 2
        try:
            d = bm[dy][dx]
        except IndexError:
            d = 0

        if c and not d:  # /* ambiguous turn */
            if (
                turnpolicy == POTRACE_TURNPOLICY_RIGHT
                or (turnpolicy == POTRACE_TURNPOLICY_BLACK and sign)
                or (turnpolicy == POTRACE_TURNPOLICY_WHITE and not sign)
                or (turnpolicy == POTRACE_TURNPOLICY_RANDOM and detrand(x, y))
                or (turnpolicy == POTRACE_TURNPOLICY_MAJORITY and majority(bm, x, y))
                or (
                    turnpolicy == POTRACE_TURNPOLICY_MINORITY and not majority(bm, x, y)
                )
            ):
                tmp = dirx  # /* right turn */
                dirx = diry
                diry = -tmp
            else:
                tmp = dirx  # /* left turn */
                dirx = -diry
                diry = tmp
        elif c:  # /* right turn */
            tmp = dirx
            dirx = diry
            diry = -tmp
        elif not d:  # /* left turn */
            tmp = dirx
            dirx = -diry
            diry = tmp

    # /* allocate new path object */
    return _Path(pt, area, sign)


@njit()
def findnext(bm: np.array) -> Optional[Tuple[Union[int], int]]:
    """
    /* find the next set pixel in a row <= y. Pixels are searched first
       left-to-right, then top-down. In other words, (x,y)<(x',y') if y>y'
       or y=y' and x<x'. If found, return 0 and store pixel in
       (*xp,*yp). Else return 1. Note that this function assumes that
       excess bytes have been cleared with bm_clearexcess. */
    """
    w = np.nonzero(bm)
    if len(w[0]) == 0:
        return None

    q = np.where(w[0] == w[0][-1])
    y = w[0][q]
    x = w[1][q]
    return y[0], x[0]


def setbbox_path(p: _Path):
    """
     /* Find the bounding box of a given path. Path is assumed to be of
    non-zero length. */
    """
    y0 = float("inf")
    y1 = 0
    x0 = float("inf")
    x1 = 0
    for k in range(len(p)):
        x = p.pt[k].x
        y = p.pt[k].y

        if x < x0:
            x0 = x
        if x > x1:
            x1 = x
        if y < y0:
            y0 = y
        if y > y1:
            y1 = y
    return x0, y0, x1, y1


def pathlist_to_tree(plist: list, bm: np.array) -> None:
    """
    /* Give a tree structure to the given path list, based on "insideness"
       testing. I.e., path A is considered "below" path B if it is inside
       path B. The input pathlist is assumed to be ordered so that "outer"
       paths occur before "inner" paths. The tree structure is stored in
       the "childlist" and "sibling" components of the path_t
       structure. The linked list structure is also changed so that
       negative path components are listed immediately after their
       positive parent.  Note: some backends may ignore the tree
       structure, others may use it e.g. to group path components. We
       assume that in the input, point 0 of each path is an "upper left"
       corner of the path, as returned by bm_to_pathlist. This makes it
       easy to find an "interior" point. The bm argument should be a
       bitmap of the correct size (large enough to hold all the paths),
       and will be used as scratch space. Return 0 on success or -1 on
       error with errno set. */
    """
    # path_t *p, *p1
    # path_t *heap, *heap1
    # path_t *cur
    # path_t *head
    # path_t **plist_hook          #/* for fast appending to linked list */
    # path_t **hook_in, **hook_out #/* for fast appending to linked list */
    # bbox_t bbox

    bm = bm.copy()

    # /* save original "next" pointers */

    for p in plist:
        p.sibling = p.next
        p.childlist = None

    heap = plist
    """
      /* the heap holds a list of lists of paths. Use "childlist" field
         for outer list, "next" field for inner list. Each of the sublists
         is to be turned into a tree. This code is messy, but it is
         actually fast. Each path is rendered exactly once. We use the
         heap to get a tail recursive algorithm: the heap holds a list of
         pathlists which still need to be transformed. */
    """
    while heap:
        # /* unlink first sublist */
        cur = heap
        heap = heap.childlist
        cur.childlist = None

        # /* unlink first path */
        head = cur
        cur = cur.next
        head.next = None

        # /* render path */
        xor_path(bm, head)
        x0, y0, x1, y1 = setbbox_path(head)

        """
        /* now do insideness test for each element of cur; append it to
       head->childlist if it's inside head, else append it to
       head->next. */
       """
        # hook_in= head.childlist
        # hook_out= head.next
        # list_forall_unlink(p, cur):
        #     if p.priv.pt[0].y <= bbox.y0:
        #         list_insert_beforehook(p, hook_out)
        #         # /* append the remainder of the list to hook_out */
        #         hook_out = cur
        #         break
        #     if (BM_GET(bm, p.priv.pt[0].x, p.priv.pt[0].y-1)):
        #         list_insert_beforehook(p, hook_in)
        #     else:
        #         list_insert_beforehook(p, hook_out)

    # /* clear bm */
    # clear_bm_with_bbox(bm, &bbox)
    #
    # #/* now schedule head->childlist and head->next for further processing */
    # if head.next:
    #     head.next.childlist = heap
    #     heap = head.next
    # if head.childlist:
    #     head.childlist.childlist = heap
    #     heap = head->childlist
    #
    # #/* copy sibling structure from "next" to "sibling" component */
    # p = plist
    # while p:
    #     p1 = p.sibling
    #     p.sibling = p.next
    #     p = p1
    #
    # """
    # /* reconstruct a new linked list ("next") structure from tree
    # ("childlist", "sibling") structure. This code is slightly messy,
    # because we use a heap to make it tail recursive: the heap
    # contains a list of childlists which still need to be
    # processed. */"""
    # heap = plist
    # if heap:
    #     heap.next = None  #/* heap is a linked list of childlists */
    # plist = None
    # plist_hook = plist
    # while heap:
    #     heap1 = heap.next
    #     for (p=heap; p; p=p->sibling):
    #         #/* p is a positive path */
    #         #/* append to linked list */
    #         list_insert_beforehook(p, plist_hook)
    #
    #         #/* go through its children */
    #     for (p1=p->childlist; p1; p1=p1->sibling):
    #         #/* append to linked list */


#         list_insert_beforehook(p1, plist_hook);
#         #/* append its childlist to heap, if non-empty */
#     if (p1.childlist):
#         list_append(path_t, heap1, p1->childlist)
#     heap = heap1


def bm_to_pathlist(
    bm: np.array, turdsize: int = 2, turnpolicy: int = POTRACE_TURNPOLICY_MINORITY
) -> list:
    """
    /* Decompose the given bitmap into paths. Returns a linked list of
    path_t objects with the fields len, pt, area, sign filled
    in. Returns 0 on success with plistp set, or -1 on error with errno
    set. */
    """
    plist = []  # /* linked list of path objects */
    original = bm.copy()

    """/* be sure the byte padding on the right is set to 0, as the fast
    pixel search below relies on it */"""
    # /* iterate through components */
    while True:
        n = findnext(bm)
        if n is None:
            break
        y, x = n
        # /* calculate the sign by looking at the original */
        sign = original[y][x]
        # /* calculate the path */
        path = findpath(bm, x, y + 1, sign, turnpolicy)
        if path is None:
            raise ValueError

        # /* update buffered image */
        xor_path(bm, path)

        # /* if it's a turd, eliminate it, else append it to the list */
        if path.area > turdsize:
            plist.append(path)

    # pathlist_to_tree(plist, original)
    return plist


# END DECOMPOSE SECTION.

# /* auxiliary functions */


def sign(x):
    if x > 0:
        return 1
    if x < 0:
        return -1
    else:
        return 0


def mod(a: int, n: int) -> int:
    """Note: the "mod" macro works correctly for
    negative a. Also note that the test for a>=n, while redundant,
    speeds up the mod function by 70% in the average case (significant
    since the program spends about 16% of its time here - or 40%
    without the test)."""
    return a % n if a >= n else a if a >= 0 else n - 1 - (-1 - a) % n


def floordiv(a: int, n: int):
    """
    The "floordiv" macro returns the largest integer <= a/n,
    and again this works correctly for negative a, as long as
    a,n are integers and n>0.
    """
    return a // n if a >= 0 else -1 - (-1 - a) // n


def interval(t: float, a: _Point, b: _Point):
    return _Point(a.x + t * (b.x - a.x), a.y + t * (b.y - a.y))


def dorth_infty(p0: _Point, p2: _Point):
    """
    return a direction that is 90 degrees counterclockwise from p2-p0,
    but then restricted to one of the major wind directions (n, nw, w, etc)
    """
    return _Point(-sign(p2.y - p0.y), sign(p2.x - p0.x))


def dpara(p0: _Point, p1: _Point, p2: _Point) -> float:
    """
    /* return (p1-p0)x(p2-p0), the area of the parallelogram */
    """
    x1 = p1.x - p0.x
    y1 = p1.y - p0.y
    x2 = p2.x - p0.x
    y2 = p2.y - p0.y
    return x1 * y2 - x2 * y1


def ddenom(p0: _Point, p2: _Point) -> float:
    """
    ddenom/dpara have the property that the square of radius 1 centered
    at p1 intersects the line p0p2 iff |dpara(p0,p1,p2)| <= ddenom(p0,p2)
    """
    r = dorth_infty(p0, p2)
    return r.y * (p2.x - p0.x) - r.x * (p2.y - p0.y)


def cyclic(a: int, b: int, c: int) -> int:
    """
    /* return 1 if a <= b < c < a, in a cyclic sense (mod n) */
    """
    if a <= c:
        return a <= b < c
    else:
        return a <= b or b < c


def pointslope(pp: _Path, i: int, j: int, ctr: _Point, dir: _Point) -> None:
    """
    determine the center and slope of the line i..j. Assume i<j. Needs
    "sum" components of p to be set.
    """

    # /* assume i<j */

    n = len(pp)
    sums = pp._sums

    r = 0  # /* rotations from i to j */

    while j >= n:
        j -= n
        r += 1

    while i >= n:
        i -= n
        r -= 1

    while j < 0:
        j += n
        r -= 1

    while i < 0:
        i += n
        r += 1

    x = sums[j + 1].x - sums[i].x + r * sums[n].x
    y = sums[j + 1].y - sums[i].y + r * sums[n].y
    x2 = sums[j + 1].x2 - sums[i].x2 + r * sums[n].x2
    xy = sums[j + 1].xy - sums[i].xy + r * sums[n].xy
    y2 = sums[j + 1].y2 - sums[i].y2 + r * sums[n].y2
    k = j + 1 - i + r * n

    ctr.x = x / k
    ctr.y = y / k

    a = float(x2 - x * x / k) / k
    b = float(xy - x * y / k) / k
    c = float(y2 - y * y / k) / k

    lambda2 = (
        a + c + math.sqrt((a - c) * (a - c) + 4 * b * b)
    ) / 2  # /* larger e.value */

    # /* now find e.vector for lambda2 */
    a -= lambda2
    c -= lambda2

    if math.fabs(a) >= math.fabs(c):
        l = math.sqrt(a * a + b * b)
        if l != 0:
            dir.x = -b / l
            dir.y = a / l
    else:
        l = math.sqrt(c * c + b * b)
        if l != 0:
            dir.x = -c / l
            dir.y = b / l
    if l == 0:
        # sometimes this can happen when k=4:
        # the two eigenvalues coincide */
        dir.x = 0
        dir.y = 0


"""
/* the type of (affine) quadratic forms, represented as symmetric 3x3
     matrices.    The value of the quadratic form at a vector (x,y) is v^t
     Q v, where v = (x,y,1)^t. */
"""


def quadform(Q: list, w: _Point) -> float:
    """Apply quadratic form Q to vector w = (w.x,w.y)"""
    v = (w.x, w.y, 1.0)
    sum = 0.0
    for i in range(3):
        for j in range(3):
            sum += v[i] * Q[i][j] * v[j]
    return sum


def xprod(p1x, p1y, p2x, p2y) -> float:
    """calculate p1 x p2"""
    return p1x * p2y - p1y * p2x


def cprod(p0: _Point, p1: _Point, p2: _Point, p3: _Point) -> float:
    """calculate (p1-p0)x(p3-p2)"""
    x1 = p1.x - p0.x
    y1 = p1.y - p0.y
    x2 = p3.x - p2.x
    y2 = p3.y - p2.y
    return x1 * y2 - x2 * y1


def iprod(p0: _Point, p1: _Point, p2: _Point) -> float:
    """calculate (p1-p0)*(p2-p0)"""
    x1 = p1.x - p0.x
    y1 = p1.y - p0.y
    x2 = p2.x - p0.x
    y2 = p2.y - p0.y
    return x1 * x2 + y1 * y2


def iprod1(p0: _Point, p1: _Point, p2: _Point, p3: _Point) -> float:
    """calculate (p1-p0)*(p3-p2)"""
    x1 = p1.x - p0.x
    y1 = p1.y - p0.y
    x2 = p3.x - p2.x
    y2 = p3.y - p2.y
    return x1 * x2 + y1 * y2


def sq(x: float) -> float:
    return x * x


def ddist(p: _Point, q: _Point) -> float:
    """calculate distance between two points"""
    return math.sqrt(sq(p.x - q.x) + sq(p.y - q.y))


def bezier(t: float, p0: _Point, p1: _Point, p2: _Point, p3: _Point) -> _Point:
    """calculate point of a bezier curve"""
    s = 1 - t

    """
    Note: a good optimizing compiler (such as gcc-3) reduces the
    following to 16 multiplications, using common subexpression
    elimination.
    """
    return _Point(
        s * s * s * p0.x
        + 3 * (s * s * t) * p1.x
        + 3 * (t * t * s) * p2.x
        + t * t * t * p3.x,
        s * s * s * p0.y
        + 3 * (s * s * t) * p1.y
        + 3 * (t * t * s) * p2.y
        + t * t * t * p3.y,
    )


def tangent(
    p0: _Point, p1: _Point, p2: _Point, p3: _Point, q0: _Point, q1: _Point
) -> float:
    """calculate the point t in [0..1] on the (convex) bezier curve
    (p0,p1,p2,p3) which is tangent to q1-q0. Return -1.0 if there is no
    solution in [0..1]."""

    # (1-t)^2 A + 2(1-t)t B + t^2 C = 0
    # a t^2 + b t + c = 0

    A = cprod(p0, p1, q0, q1)
    B = cprod(p1, p2, q0, q1)
    C = cprod(p2, p3, q0, q1)

    a = A - 2 * B + C
    b = -2 * A + 2 * B
    c = A

    d = b * b - 4 * a * c

    if a == 0 or d < 0:
        return -1.0

    s = math.sqrt(d)

    r1 = (-b + s) / (2 * a)
    r2 = (-b - s) / (2 * a)

    if 0 <= r1 <= 1:
        return r1
    elif 0 <= r2 <= 1:
        return r2
    else:
        return -1.0


"""
/* ---------------------------------------------------------------------- */
/* Stage 1: determine the straight subpaths (Sec. 2.2.1). Fill in the
     "lon" component of a path object (based on pt/len).	For each i,
     lon[i] is the furthest index such that a straight line can be drawn
     from i to lon[i]. Return 1 on error with errno set, else 0. */

/* this algorithm depends on the fact that the existence of straight
     subpaths is a triplewise property. I.e., there exists a straight
     line through squares i0,...,in iff there exists a straight line
     through i,j,k, for all i0<=i<j<k<=in. (Proof?) */

/* this implementation of calc_lon is O(n^2). It replaces an older
     O(n^3) version. A "constraint" means that future points must
     satisfy xprod(constraint[0], cur) >= 0 and xprod(constraint[1],
     cur) <= 0. */

/* Remark for Potrace 1.1: the current implementation of calc_lon is
     more complex than the implementation found in Potrace 1.0, but it
     is considerably faster. The introduction of the "nc" data structure
     means that we only have to test the constraints for "corner"
     points. On a typical input file, this speeds up the calc_lon
     function by a factor of 31.2, thereby decreasing its time share
     within the overall Potrace algorithm from 72.6% to 7.82%, and
     speeding up the overall algorithm by a factor of 3.36. On another
     input file, calc_lon was sped up by a factor of 6.7, decreasing its
     time share from 51.4% to 13.61%, and speeding up the overall
     algorithm by a factor of 1.78. In any case, the savings are
     substantial. */

"""


# ----------------------------------------------------------------------


def _calc_sums(path: _Path) -> int:
    """Preparation: fill in the sum* fields of a path (used for later
    rapid summing). Return 0 on success, 1 with errno set on
    failure."""
    n = len(path)
    path._sums = [_Sums() for i in range(len(path) + 1)]

    # origin
    path._x0 = path.pt[0].x
    path._y0 = path.pt[0].y

    # /* preparatory computation for later fast summing */
    path._sums[0].x2 = 0
    path._sums[0].xy = 0
    path._sums[0].y2 = 0
    path._sums[0].x = 0
    path._sums[0].y = 0
    for i in range(n):
        x = path.pt[i].x - path._x0
        y = path.pt[i].y - path._y0
        path._sums[i + 1].x = path._sums[i].x + x
        path._sums[i + 1].y = path._sums[i].y + y
        path._sums[i + 1].x2 = path._sums[i].x2 + float(x * x)
        path._sums[i + 1].xy = path._sums[i].xy + float(x * y)
        path._sums[i + 1].y2 = path._sums[i].y2 + float(y * y)
    return 0


def _calc_lon(pp: _Path) -> int:
    """initialize the nc data structure. Point from each point to the
    furthest future point to which it is connected by a vertical or
    horizontal segment. We take advantage of the fact that there is
    always a direction change at 0 (due to the path decomposition
    algorithm). But even if this were not so, there is no harm, as
    in practice, correctness does not depend on the word "furthest"
    above.
        returns 0 on success, 1 on error with errno set
    """

    pt = pp.pt
    n = len(pp)
    ct = [0, 0, 0, 0]
    pivk = [None] * n  # pivk[n]
    nc = [None] * n  # nc[n]: next corner

    k = 0
    for i in range(n - 1, -1, -1):
        if pt[i].x != pt[k].x and pt[i].y != pt[k].y:
            k = i + 1  # /* necessarily i<n-1 in this case */
        nc[i] = k

    pp._lon = [None] * n

    # determine pivot points: for each i, let pivk[i] be the furthest k
    # such that all j with i<j<k lie on a line connecting i,k.

    for i in range(n - 1, -1, -1):
        ct[0] = ct[1] = ct[2] = ct[3] = 0

        # keep track of "directions" that have occurred
        dir = int(
            (3 + 3 * (pt[mod(i + 1, n)].x - pt[i].x) + (pt[mod(i + 1, n)].y - pt[i].y))
            // 2
        )
        ct[dir] += 1

        constraint0x = 0
        constraint0y = 0
        constraint1x = 0
        constraint1y = 0

        # find the next k such that no straight line from i to k
        k = nc[i]
        k1 = i
        while True:
            break_inner_loop_and_continue = False
            dir = int(3 + 3 * sign(pt[k].x - pt[k1].x) + sign(pt[k].y - pt[k1].y)) // 2
            ct[dir] += 1

            # if all four "directions" have occurred, cut this path
            if ct[0] and ct[1] and ct[2] and ct[3]:
                pivk[i] = k1
                break_inner_loop_and_continue = True
                break  # goto foundk;

            cur_x = pt[k].x - pt[i].x
            cur_y = pt[k].y - pt[i].y

            if (
                xprod(constraint0x, constraint0y, cur_x, cur_y) < 0
                or xprod(constraint1x, constraint1y, cur_x, cur_y) > 0
            ):
                break
            # see if current constraint is violated
            # else, update constraint
            if abs(cur_x) <= 1 and abs(cur_y) <= 1:
                pass  # /* no constraint */
            else:
                off_x = cur_x + (1 if (cur_y >= 0 and (cur_y > 0 or cur_x < 0)) else -1)
                off_y = cur_y + (1 if (cur_x <= 0 and (cur_x < 0 or cur_y < 0)) else -1)
                if xprod(constraint0x, constraint0y, off_x, off_y) >= 0:
                    constraint0x = off_x
                    constraint0y = off_y
                off_x = cur_x + (1 if (cur_y <= 0 and (cur_y < 0 or cur_x < 0)) else -1)
                off_y = cur_y + (1 if (cur_x >= 0 and (cur_x > 0 or cur_y < 0)) else -1)
                if xprod(constraint1x, constraint1y, off_x, off_y) <= 0:
                    constraint1x = off_x
                    constraint1y = off_y
            k1 = k
            k = nc[k1]
            if not cyclic(k, i, k1):
                break
        if break_inner_loop_and_continue:
            # This previously was a goto to the end of the for i statement.
            continue
        # constraint_viol:
        """k1 was the last "corner" satisfying the current constraint, and
        k is the first one violating it. We now need to find the last
        point along k1..k which satisfied the constraint."""
        # dk: direction of k-k1
        dk_x = sign(pt[k].x - pt[k1].x)
        dk_y = sign(pt[k].y - pt[k1].y)
        cur_x = pt[k1].x - pt[i].x
        cur_y = pt[k1].y - pt[i].y
        """find largest integer j such that xprod(constraint[0], cur+j*dk) >= 0
        and xprod(constraint[1], cur+j*dk) <= 0. Use bilinearity of xprod. */"""
        a = xprod(constraint0x, constraint0y, cur_x, cur_y)
        b = xprod(constraint0x, constraint0y, dk_x, dk_y)
        c = xprod(constraint1x, constraint1y, cur_x, cur_y)
        d = xprod(constraint1x, constraint1y, dk_x, dk_y)
        """find largest integer j such that a+j*b>=0 and c+j*d<=0. This
        can be solved with integer arithmetic."""
        j = INFTY
        if b < 0:
            j = floordiv(a, -b)
        if d > 0:
            j = min(j, floordiv(-c, d))
        pivk[i] = mod(k1 + j, n)
        # foundk:
        # /* for i */

    """/* clean up: for each i, let lon[i] be the largest k such that for
         all i' with i<=i'<k, i'<k<=pivk[i']. */"""

    j = pivk[n - 1]
    pp._lon[n - 1] = j
    for i in range(n - 2, -1, -1):
        if cyclic(i + 1, pivk[i], j):
            j = pivk[i]
        pp._lon[i] = j

    i = n - 1
    while cyclic(mod(i + 1, n), j, pp._lon[i]):
        pp._lon[i] = j
        i -= 1
    return 0


"""
/* ---------------------------------------------------------------------- */
/* Stage 2: calculate the optimal polygon (Sec. 2.2.2-2.2.4). */
"""


def penalty3(pp: _Path, i: int, j: int) -> float:
    """Auxiliary function: calculate the penalty of an edge from i to j in
    the given path. This needs the "lon" and "sum*" data."""
    n = len(pp)
    pt = pp.pt
    sums = pp._sums

    # /* assume 0<=i<j<=n    */

    r = 0  # /* rotations from i to j */
    if j >= n:
        j -= n
        r = 1

    # /* critical inner loop: the "if" gives a 4.6 percent speedup */
    if r == 0:
        x = sums[j + 1].x - sums[i].x
        y = sums[j + 1].y - sums[i].y
        x2 = sums[j + 1].x2 - sums[i].x2
        xy = sums[j + 1].xy - sums[i].xy
        y2 = sums[j + 1].y2 - sums[i].y2
        k = j + 1 - i
    else:
        x = sums[j + 1].x - sums[i].x + sums[n].x
        y = sums[j + 1].y - sums[i].y + sums[n].y
        x2 = sums[j + 1].x2 - sums[i].x2 + sums[n].x2
        xy = sums[j + 1].xy - sums[i].xy + sums[n].xy
        y2 = sums[j + 1].y2 - sums[i].y2 + sums[n].y2
        k = j + 1 - i + n

    px = (pt[i].x + pt[j].x) / 2.0 - pt[0].x
    py = (pt[i].y + pt[j].y) / 2.0 - pt[0].y
    ey = pt[j].x - pt[i].x
    ex = -(pt[j].y - pt[i].y)

    a = (x2 - 2 * x * px) / k + px * px
    b = (xy - x * py - y * px) / k + px * py
    c = (y2 - 2 * y * py) / k + py * py

    s = ex * ex * a + 2 * ex * ey * b + ey * ey * c
    return math.sqrt(s)


def _bestpolygon(pp: _Path) -> int:
    """
    /* find the optimal polygon. Fill in the m and po components. Return 1
         on failure with errno set, else 0. Non-cyclic version: assumes i=0
         is in the polygon. Fixme: implement cyclic version. */
    """
    n = len(pp)
    pen = [None] * (n + 1)  # /* pen[n+1]: penalty vector */
    prev = [None] * (n + 1)  # /* prev[n+1]: best path pointer vector */
    clip0 = [None] * n  # /* clip0[n]: longest segment pointer, non-cyclic */
    clip1 = [None] * (n + 1)  # /* clip1[n+1]: backwards segment pointer, non-cyclic */
    seg0 = [None] * (n + 1)  # /* seg0[m+1]: forward segment bounds, m<=n */
    seg1 = [None] * (n + 1)  # /* seg1[m+1]: backward segment bounds, m<=n */

    # /* calculate clipped paths */
    for i in range(n):
        c = mod(pp._lon[mod(i - 1, n)] - 1, n)
        if c == i:
            c = mod(i + 1, n)
        if c < i:
            clip0[i] = n
        else:
            clip0[i] = c

    # /* calculate backwards path clipping, non-cyclic. j <= clip0[i] iff
    # clip1[j] <= i, for i,j=0..n. */
    j = 1
    for i in range(n):
        while j <= clip0[i]:
            clip1[j] = i
            j += 1

    # calculate seg0[j] = longest path from 0 with j segments */
    i = 0
    j = 0
    while i < n:
        seg0[j] = i
        i = clip0[i]
        j += 1
    seg0[j] = n
    m = j

    # calculate seg1[j] = longest path to n with m-j segments */
    i = n
    for j in range(m, 0, -1):
        seg1[j] = i
        i = clip1[i]
    seg1[0] = 0

    """now find the shortest path with m segments, based on penalty3 */
    /* note: the outer 2 loops jointly have at most n iterations, thus
         the worst-case behavior here is quadratic. In practice, it is
         close to linear since the inner loop tends to be short. */
         """
    pen[0] = 0
    for j in range(1, m + 1):
        for i in range(seg1[j], seg0[j] + 1):
            best = -1
            for k in range(seg0[j - 1], clip1[i] - 1, -1):
                thispen = penalty3(pp, k, i) + pen[k]
                if best < 0 or thispen < best:
                    prev[i] = k
                    best = thispen
            pen[i] = best

    pp._m = m
    pp._po = [None] * m

    # /* read off shortest path */
    i = n
    j = m - 1
    while i > 0:
        i = prev[i]
        pp._po[j] = i
        j -= 1
    return 0


"""
/* ---------------------------------------------------------------------- */
/* Stage 3: vertex adjustment (Sec. 2.3.1). */

"""


def _adjust_vertices(pp: _Path) -> int:
    """
    /* Adjust vertices of optimal polygon: calculate the intersection of
     the two "optimal" line segments, then move it into the unit square
     if it lies outside. Return 1 with errno set on error; 0 on
     success. */
    """
    m = pp._m
    po = pp._po
    n = len(pp)
    pt = pp.pt  # point_t
    x0 = pp._x0
    y0 = pp._y0

    ctr = [_Point() for i in range(m)]  # /* ctr[m] */
    dir = [_Point() for i in range(m)]  # /* dir[m] */
    q = [
        [[0.0 for a in range(3)] for b in range(3)] for c in range(m)
    ]  # quadform_t/* q[m] */
    v = [0.0, 0.0, 0.0]
    s = _Point(0, 0)
    pp._curve = _Curve(m)

    # /* calculate "optimal" point-slope representation for each line segment */
    for i in range(m):
        j = po[mod(i + 1, m)]
        j = mod(j - po[i], n) + po[i]
        pointslope(pp, po[i], j, ctr[i], dir[i])

        # /* represent each line segment as a singular quadratic form;
        # the distance of a point (x,y) from the line segment will be
        # (x,y,1)Q(x,y,1)^t, where Q=q[i]. */
    for i in range(m):
        d = sq(dir[i].x) + sq(dir[i].y)
        if d == 0.0:
            for j in range(3):
                for k in range(3):
                    q[i][j][k] = 0
        else:
            v[0] = dir[i].y
            v[1] = -dir[i].x
            v[2] = -v[1] * ctr[i].y - v[0] * ctr[i].x
            for l in range(3):
                for k in range(3):
                    q[i][l][k] = v[l] * v[k] / d

    """/* now calculate the "intersections" of consecutive segments.
         Instead of using the actual intersection, we find the point
         within a given unit square which minimizes the square distance to
         the two lines. */"""
    Q = [[0.0 for a in range(3)] for b in range(3)]
    for i in range(m):
        # double min, cand; #/* minimum and candidate for minimum of quad. form */
        # double xmin, ymin;	#/* coordinates of minimum */

        # /* let s be the vertex, in coordinates relative to x0/y0 */
        s.x = pt[po[i]].x - x0
        s.y = pt[po[i]].y - y0

        # /* intersect segments i-1 and i */

        j = mod(i - 1, m)

        # /* add quadratic forms */
        for l in range(3):
            for k in range(3):
                Q[l][k] = q[j][l][k] + q[i][l][k]

        while True:
            # /* minimize the quadratic form Q on the unit square */
            # /* find intersection */

            det = Q[0][0] * Q[1][1] - Q[0][1] * Q[1][0]
            w = None
            if det != 0.0:
                w = _Point(
                    (-Q[0][2] * Q[1][1] + Q[1][2] * Q[0][1]) / det,
                    (Q[0][2] * Q[1][0] - Q[1][2] * Q[0][0]) / det,
                )
                break

            # /* matrix is singular - lines are parallel. Add another,
            # orthogonal axis, through the center of the unit square */
            if Q[0][0] > Q[1][1]:
                v[0] = -Q[0][1]
                v[1] = Q[0][0]
            elif Q[1][1]:
                v[0] = -Q[1][1]
                v[1] = Q[1][0]
            else:
                v[0] = 1
                v[1] = 0
            d = sq(v[0]) + sq(v[1])
            v[2] = -v[1] * s.y - v[0] * s.x
            for l in range(3):
                for k in range(3):
                    Q[l][k] += v[l] * v[k] / d
        dx = math.fabs(w.x - s.x)
        dy = math.fabs(w.y - s.y)
        if dx <= 0.5 and dy <= 0.5:
            pp._curve[i].vertex.x = w.x + x0
            pp._curve[i].vertex.y = w.y + y0
            continue

        # /* the minimum was not in the unit square; now minimize quadratic
        # on boundary of square */
        min = quadform(Q, s)
        xmin = s.x
        ymin = s.y

        if Q[0][0] != 0.0:
            for z in range(2):  # /* value of the y-coordinate */
                w.y = s.y - 0.5 + z
                w.x = -(Q[0][1] * w.y + Q[0][2]) / Q[0][0]
                dx = math.fabs(w.x - s.x)
                cand = quadform(Q, w)
                if dx <= 0.5 and cand < min:
                    min = cand
                    xmin = w.x
                    ymin = w.y
        if Q[1][1] != 0.0:
            for z in range(2):  # /* value of the x-coordinate */
                w.x = s.x - 0.5 + z
                w.y = -(Q[1][0] * w.x + Q[1][2]) / Q[1][1]
                dy = math.fabs(w.y - s.y)
                cand = quadform(Q, w)
                if dy <= 0.5 and cand < min:
                    min = cand
                    xmin = w.x
                    ymin = w.y
        # /* check four corners */
        for l in range(2):
            for k in range(2):
                w = _Point(s.x - 0.5 + l, s.y - 0.5 + k)
                cand = quadform(Q, w)
                if cand < min:
                    min = cand
                    xmin = w.x
                    ymin = w.y
        pp._curve[i].vertex.x = xmin + x0
        pp._curve[i].vertex.y = ymin + y0
    return 0


"""
/* ---------------------------------------------------------------------- */
/* Stage 4: smoothing and corner analysis (Sec. 2.3.3) */
"""


def reverse(curve: _Curve) -> None:
    """/* reverse orientation of a path */"""
    m = curve.n
    i = 0
    j = m - 1
    while i < j:
        tmp = curve[i].vertex
        curve[i].vertex = curve[j].vertex
        curve[j].vertex = tmp
        i += 1
        j -= 1


# /* Always succeeds */


def _smooth(curve: _Curve, alphamax: float) -> None:
    m = curve.n

    # /* examine each vertex and find its best fit */
    for i in range(m):
        j = mod(i + 1, m)
        k = mod(i + 2, m)
        p4 = interval(1 / 2.0, curve[k].vertex, curve[j].vertex)

        denom = ddenom(curve[i].vertex, curve[k].vertex)
        if denom != 0.0:
            dd = dpara(curve[i].vertex, curve[j].vertex, curve[k].vertex) / denom
            dd = math.fabs(dd)
            alpha = (1 - 1.0 / dd) if dd > 1 else 0
            alpha = alpha / 0.75
        else:
            alpha = 4 / 3.0
        curve[j].alpha0 = alpha  # /* remember "original" value of alpha */

        if alpha >= alphamax:  # /* pointed corner */
            curve[j].tag = POTRACE_CORNER
            curve[j].c[1] = curve[j].vertex
            curve[j].c[2] = p4
        else:
            if alpha < 0.55:
                alpha = 0.55
            elif alpha > 1:
                alpha = 1
            p2 = interval(0.5 + 0.5 * alpha, curve[i].vertex, curve[j].vertex)
            p3 = interval(0.5 + 0.5 * alpha, curve[k].vertex, curve[j].vertex)
            curve[j].tag = POTRACE_CURVETO
            curve[j].c[0] = p2
            curve[j].c[1] = p3
            curve[j].c[2] = p4
        curve[j].alpha = alpha  # /* store the "cropped" value of alpha */
        curve[j].beta = 0.5
    curve.alphacurve = True


"""
/* ---------------------------------------------------------------------- */
/* Stage 5: Curve optimization (Sec. 2.4) */
"""


class opti_t:
    def __init__(self):
        self.pen = 0  # /* penalty */
        self.c = [_Point(0, 0), _Point(0, 0)]  # /* curve parameters */
        self.t = 0  # /* curve parameters */
        self.s = 0  # /* curve parameters */
        self.alpha = 0  # /* curve parameter */


def opti_penalty(
    pp: _Path,
    i: int,
    j: int,
    res: opti_t,
    opttolerance: float,
    convc: int,
    areac: float,
) -> int:
    """
    /* calculate best fit from i+.5 to j+.5.    Assume i<j (cyclically).
     Return 0 and set badness and parameters (alpha, beta), if
     possible. Return 1 if impossible. */
    """

    m = pp._curve.n

    # /* check convexity, corner-freeness, and maximum bend < 179 degrees */

    if i == j:  # sanity - a full loop can never be an opticurve
        return 1

    k = i
    i1 = mod(i + 1, m)
    k1 = mod(k + 1, m)
    conv = convc[k1]
    if conv == 0:
        return 1
    d = ddist(pp._curve[i].vertex, pp._curve[i1].vertex)
    k = k1
    while k != j:
        k1 = mod(k + 1, m)
        k2 = mod(k + 2, m)
        if convc[k1] != conv:
            return 1
        if (
            sign(
                cprod(
                    pp._curve[i].vertex,
                    pp._curve[i1].vertex,
                    pp._curve[k1].vertex,
                    pp._curve[k2].vertex,
                )
            )
            != conv
        ):
            return 1
        if (
            iprod1(
                pp._curve[i].vertex,
                pp._curve[i1].vertex,
                pp._curve[k1].vertex,
                pp._curve[k2].vertex,
            )
            < d * ddist(pp._curve[k1].vertex, pp._curve[k2].vertex) * COS179
        ):
            return 1
        k = k1

    # /* the curve we're working in: */
    p0 = pp._curve[mod(i, m)].c[2]
    p1 = pp._curve[mod(i + 1, m)].vertex
    p2 = pp._curve[mod(j, m)].vertex
    p3 = pp._curve[mod(j, m)].c[2]

    # /* determine its area */
    area = areac[j] - areac[i]
    area -= dpara(pp._curve[0].vertex, pp._curve[i].c[2], pp._curve[j].c[2]) / 2
    if i >= j:
        area += areac[m]

    # /* find intersection o of p0p1 and p2p3. Let t,s such that
    # o =interval(t,p0,p1) = interval(s,p3,p2). Let A be the area of the
    # triangle (p0,o,p3). */

    A1 = dpara(p0, p1, p2)
    A2 = dpara(p0, p1, p3)
    A3 = dpara(p0, p2, p3)
    # /* A4 = dpara(p1, p2, p3); */
    A4 = A1 + A3 - A2

    if A2 == A1:  # this should never happen
        return 1

    t = A3 / (A3 - A4)
    s = A2 / (A2 - A1)
    A = A2 * t / 2.0

    if A == 0.0:  # this should never happen
        return 1

    R = area / A  # /* relative area */
    alpha = 2 - math.sqrt(4 - R / 0.3)  # /* overall alpha for p0-o-p3 curve */

    res.c[0] = interval(t * alpha, p0, p1)
    res.c[1] = interval(s * alpha, p3, p2)
    res.alpha = alpha
    res.t = t
    res.s = s

    p1 = res.c[0]
    p1 = _Point(p1.x, p1.y)
    p2 = res.c[1]  # /* the proposed curve is now (p0,p1,p2,p3) */
    p2 = _Point(p2.x, p2.y)

    res.pen = 0

    # /* calculate penalty */
    # /* check tangency with edges */
    k = mod(i + 1, m)
    while k != j:
        k1 = mod(k + 1, m)
        t = tangent(p0, p1, p2, p3, pp._curve[k].vertex, pp._curve[k1].vertex)
        if t < -0.5:
            return 1
        pt = bezier(t, p0, p1, p2, p3)
        d = ddist(pp._curve[k].vertex, pp._curve[k1].vertex)
        if d == 0.0:  # /* this should never happen */
            return 1
        d1 = dpara(pp._curve[k].vertex, pp._curve[k1].vertex, pt) / d
        if math.fabs(d1) > opttolerance:
            return 1
        if (
            iprod(pp._curve[k].vertex, pp._curve[k1].vertex, pt) < 0
            or iprod(pp._curve[k1].vertex, pp._curve[k].vertex, pt) < 0
        ):
            return 1
        res.pen += sq(d1)
        k = k1

    # /* check corners */
    k = i
    while k != j:
        k1 = mod(k + 1, m)
        t = tangent(p0, p1, p2, p3, pp._curve[k].c[2], pp._curve[k1].c[2])
        if t < -0.5:
            return 1
        pt = bezier(t, p0, p1, p2, p3)
        d = ddist(pp._curve[k].c[2], pp._curve[k1].c[2])
        if d == 0.0:  # /* this should never happen */
            return 1
        d1 = dpara(pp._curve[k].c[2], pp._curve[k1].c[2], pt) / d
        d2 = dpara(pp._curve[k].c[2], pp._curve[k1].c[2], pp._curve[k1].vertex) / d
        d2 *= 0.75 * pp._curve[k1].alpha
        if d2 < 0:
            d1 = -d1
            d2 = -d2
        if d1 < d2 - opttolerance:
            return 1
        if d1 < d2:
            res.pen += sq(d1 - d2)
        k = k1
    return 0


def _opticurve(pp: _Path, opttolerance: float) -> int:
    """
    optimize the path p, replacing sequences of Bezier segments by a
    single segment when possible. Return 0 on success, 1 with errno set
    on failure.
    """
    m = pp._curve.n
    pt = [0] * (m + 1)  # /* pt[m+1] */
    pen = [0.0] * (m + 1)  # /* pen[m+1] */
    len = [0] * (m + 1)  # /* len[m+1] */
    opt = [None] * (m + 1)  # /* opt[m+1] */

    convc = [0.0] * m  # /* conv[m]: pre-computed convexities */
    areac = [0.0] * (m + 1)  # /* cumarea[m+1]: cache for fast area computation */

    # /* pre-calculate convexity: +1 = right turn, -1 = left turn, 0 = corner */
    for i in range(m):
        if pp._curve[i].tag == POTRACE_CURVETO:
            convc[i] = sign(
                dpara(
                    pp._curve[mod(i - 1, m)].vertex,
                    pp._curve[i].vertex,
                    pp._curve[mod(i + 1, m)].vertex,
                )
            )
        else:
            convc[i] = 0

    # /* pre-calculate areas */
    area = 0.0
    areac[0] = 0.0
    p0 = pp._curve[0].vertex
    for i in range(m):
        i1 = mod(i + 1, m)
        if pp._curve[i1].tag == POTRACE_CURVETO:
            alpha = pp._curve[i1].alpha
            area += (
                0.3
                * alpha
                * (4 - alpha)
                * dpara(pp._curve[i].c[2], pp._curve[i1].vertex, pp._curve[i1].c[2])
                / 2
            )
            area += dpara(p0, pp._curve[i].c[2], pp._curve[i1].c[2]) / 2
        areac[i + 1] = area
    pt[0] = -1
    pen[0] = 0
    len[0] = 0

    # /* Fixme: we always start from a fixed point
    # -- should find the best curve cyclically */

    o = None
    for j in range(1, m + 1):
        # /* calculate best path from 0 to j */
        pt[j] = j - 1
        pen[j] = pen[j - 1]
        len[j] = len[j - 1] + 1
        for i in range(j - 2, -1, -1):
            if o is None:
                o = opti_t()
            if opti_penalty(pp, i, mod(j, m), o, opttolerance, convc, areac):
                break
            if len[j] > len[i] + 1 or (
                len[j] == len[i] + 1 and pen[j] > pen[i] + o.pen
            ):
                opt[j] = o
                pt[j] = i
                pen[j] = pen[i] + o.pen
                len[j] = len[i] + 1
                o = None
    om = len[m]
    pp._ocurve = _Curve(om)
    s = [None] * om
    t = [None] * om

    j = m
    for i in range(om - 1, -1, -1):
        if pt[j] == j - 1:
            pp._ocurve[i].tag = pp._curve[mod(j, m)].tag
            pp._ocurve[i].c[0] = pp._curve[mod(j, m)].c[0]
            pp._ocurve[i].c[1] = pp._curve[mod(j, m)].c[1]
            pp._ocurve[i].c[2] = pp._curve[mod(j, m)].c[2]
            pp._ocurve[i].vertex = pp._curve[mod(j, m)].vertex
            pp._ocurve[i].alpha = pp._curve[mod(j, m)].alpha
            pp._ocurve[i].alpha0 = pp._curve[mod(j, m)].alpha0
            pp._ocurve[i].beta = pp._curve[mod(j, m)].beta
            s[i] = t[i] = 1.0
        else:
            pp._ocurve[i].tag = POTRACE_CURVETO
            pp._ocurve[i].c[0] = opt[j].c[0]
            pp._ocurve[i].c[1] = opt[j].c[1]
            pp._ocurve[i].c[2] = pp._curve[mod(j, m)].c[2]
            pp._ocurve[i].vertex = interval(
                opt[j].s, pp._curve[mod(j, m)].c[2], pp._curve[mod(j, m)].vertex
            )
            pp._ocurve[i].alpha = opt[j].alpha
            pp._ocurve[i].alpha0 = opt[j].alpha
            s[i] = opt[j].s
            t[i] = opt[j].t
        j = pt[j]

    # /* calculate beta parameters */
    for i in range(om):
        i1 = mod(i + 1, om)
        pp._ocurve[i].beta = s[i] / (s[i] + t[i1])
    pp._ocurve.alphacurve = True
    return 0


# /* ---------------------------------------------------------------------- */


def process_path(
    plist: list,
    alphamax=1.0,
    opticurve=True,
    opttolerance=0.2,
) -> int:
    """/* return 0 on success, 1 on error with errno set. */"""

    def TRY(x):
        if x:
            raise ValueError

    # /* call downstream function with each path */
    for p in plist:
        TRY(_calc_sums(p))
        TRY(_calc_lon(p))
        TRY(_bestpolygon(p))
        TRY(_adjust_vertices(p))
        if not p.sign:  # /* reverse orientation of negative paths */
            reverse(p._curve)
        _smooth(p._curve, alphamax)
        if opticurve:
            TRY(_opticurve(p, opttolerance))
            p._fcurve = p._ocurve
        else:
            p._fcurve = p._curve
    return 0


# END TRACE SECTION.