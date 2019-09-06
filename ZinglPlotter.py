from math import floor, sqrt


def plot_line(x0, y0, x1, y1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)

    if x0 < x1:
        sx = 1
    else:
        sx = -1
    if y0 < y1:
        sy = 1
    else:
        sy = -1

    err = dx + dy  # error value e_xy

    while True:  # /* loop */
        yield x0, y0, 1
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:  # e_xy+e_y < 0
            err += dy
            x0 += sx
        if e2 <= dx:  # e_xy+e_y < 0
            err += dx
            y0 += sy


def plot_quad_bezier_seg(x0, y0, x1, y1, x2, y2):
    """plot a limited quadratic Bezier segment"""
    sx = x2 - x1
    sy = y2 - y1
    xx = x0 - x1
    yy = y0 - y1
    xy = 0  # relative values for checks */
    dx = 0
    dy = 0
    err = 0
    cur = xx * sy - yy * sx  # /* curvature */
    points = None

    assert (xx * sx <= 0 and yy * sy <= 0)  # /* sign of gradient must not change */

    if sx * sx + sy * sy > xx * xx + yy * yy:  # /* begin with shorter part */
        x2 = x0
        x0 = sx + x1
        y2 = y0
        y0 = sy + y1
        cur = -cur  # /* swap P0 P2 */
        points = []
    if cur != 0:  # /* no straight line */
        xx += sx
        if x0 < x2:
            sx = 1  # /* x step direction */
        else:
            sx = -1  # /* x step direction */
        xx *= sx
        yy += sy
        if y0 < y2:
            sy = 1
        else:
            sy = -1
        yy *= sy  # /* y step direction */
        xy = 2 * xx * yy
        xx *= xx
        yy *= yy  # /* differences 2nd degree */
        if cur * sx * sy < 0:  # /* negated curvature? */
            xx = -xx
            yy = -yy
            xy = -xy
            cur = -cur
        dx = 4.0 * sy * cur * (x1 - x0) + xx - xy  # /* differences 1st degree */
        dy = 4.0 * sx * cur * (y0 - y1) + yy - xy
        xx += xx
        yy += yy
        err = dx + dy + xy  # /* error 1st step */
        while True:
            if points is None:
                yield x0, y0, 1  # /* plot curve */
            else:
                points.append((x0, y0, 1))
            if x0 == x2 and y0 == y2:
                if points is not None:
                    for plot in reversed(points):
                        yield plot
                return  # /* last pixel -> curve finished */
            y1 = 2 * err < dx  # /* save value for test of y step */
            if 2 * err > dy:
                x0 += sx
                dx -= xy
                dy += yy
                err += dy
                # /* x step */
            if y1 != 0:
                y0 += sy
                dy -= xy
                dx += xx
                err += dx
                # /* y step */
            if not (dy < 0 and dx > 0):  # /* gradient negates -> algorithm fails */
                break
    for plot in plot_line(x0, y0, x2, y2):  # /* plot remaining part to end */:
        if points is None:
            yield plot  # /* plot curve */
        else:
            points.append(plot)  # plotLine(x0,y0, x2,y2) #/* plot remaining part to end */
    if points is not None:
        for plot in reversed(points):
            yield plot


def plot_quad_bezier(x0, y0, x1, y1, x2, y2):
    """plot any quadratic Bezier curve"""
    x = x0 - x1
    y = y0 - y1
    t = x0 - 2 * x1 + x2
    r = 0

    if x * (x2 - x1) > 0:  # /* horizontal cut at P4? */
        if y * (y2 - y1) > 0:  # /* vertical cut at P6 too? */
            if abs((y0 - 2 * y1 + y2) / t * x) > abs(y):  # /* which first? */
                x0 = x2
                x2 = x + x1
                y0 = y2
                y2 = y + y1  # /* swap points */
                # /* now horizontal cut at P4 comes first */
        t = (x0 - x1) / t
        r = (1 - t) * ((1 - t) * y0 + 2.0 * t * y1) + t * t * y2  # /* By(t=P4) */
        t = (x0 * x2 - x1 * x1) * t / (x0 - x1)  # /* gradient dP4/dx=0 */
        x = floor(t + 0.5)
        y = floor(r + 0.5)
        r = (y1 - y0) * (t - x0) / (x1 - x0) + y0  # /* intersect P3 | P0 P1 */
        for plot in plot_quad_bezier_seg(x0, y0, x, floor(r + 0.5), x, y):
            yield plot
        r = (y1 - y2) * (t - x2) / (x1 - x2) + y2  # /* intersect P4 | P1 P2 */
        x0 = x1 = x
        y0 = y
        y1 = floor(r + 0.5)  # /* P0 = P4, P1 = P8 */
    if (y0 - y1) * (y2 - y1) > 0:  # /* vertical cut at P6? */
        t = y0 - 2 * y1 + y2
        t = (y0 - y1) / t
        r = (1 - t) * ((1 - t) * x0 + 2.0 * t * x1) + t * t * x2  # /* Bx(t=P6) */
        t = (y0 * y2 - y1 * y1) * t / (y0 - y1)  # /* gradient dP6/dy=0 */
        x = floor(r + 0.5)
        y = floor(t + 0.5)
        r = (x1 - x0) * (t - y0) / (y1 - y0) + x0  # /* intersect P6 | P0 P1 */
        for plot in plot_quad_bezier_seg(x0, y0, floor(r + 0.5), y, x, y):
            yield plot
        r = (x1 - x2) * (t - y2) / (y1 - y2) + x2  # /* intersect P7 | P1 P2 */
        x0 = x
        x1 = floor(r + 0.5)
        y0 = y1 = y  # /* P0 = P6, P1 = P7 */
    for plot in plot_quad_bezier_seg(x0, y0, x1, y1, x2, y2):  # /* remaining part */
        yield plot


def plot_cubic_bezier_seg(x0, y0, x1, y1, x2, y2, x3, y3):
    """plot limited cubic Bezier segment"""
    second_leg = []
    f = 0
    fx = 0
    fy = 0
    leg = 1
    if x0 < x3:
        sx = 1
    else:
        sx = -1
    if y0 < y3:
        sy = 1  # /* step direction */
    else:
        sy = -1  # /* step direction */
    xc = -abs(x0 + x1 - x2 - x3)
    xa = xc - 4 * sx * (x1 - x2)
    xb = sx * (x0 - x1 - x2 + x3)
    yc = -abs(y0 + y1 - y2 - y3)
    ya = yc - 4 * sy * (y1 - y2)
    yb = sy * (y0 - y1 - y2 + y3)
    ab = 0
    ac = 0
    bc = 0
    cb = 0
    xx = 0
    xy = 0
    yy = 0
    dx = 0
    dy = 0
    ex = 0
    pxy = 0
    EP = 0.01
    # /* check for curve restrains */
    # /* slope P0-P1 == P2-P3 and  (P0-P3 == P1-P2    or  no slope change)
    # if (x1 - x0) * (x2 - x3) < EP and ((x3 - x0) * (x1 - x2) < EP or xb * xb < xa * xc + EP):
    #     return
    # if (y1 - y0) * (y2 - y3) < EP and ((y3 - y0) * (y1 - y2) < EP or yb * yb < ya * yc + EP):
    #     return

    if xa == 0 and ya == 0:  # /* quadratic Bezier */
        # return plot_quad_bezier_seg(x0, y0, (3 * x1 - x0) >> 1, (3 * y1 - y0) >> 1, x3, y3)
        sx = floor((3 * x1 - x0 + 1) / 2)
        sy = floor((3 * y1 - y0 + 1) / 2)  # /* new midpoint */

        for plot in plot_quad_bezier_seg(x0, y0, sx, sy, x3, y3):
            yield plot
        return
    x1 = (x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0) + 1  # /* line lengths */
    x2 = (x2 - x3) * (x2 - x3) + (y2 - y3) * (y2 - y3) + 1

    while True:  # /* loop over both ends */
        ab = xa * yb - xb * ya
        ac = xa * yc - xc * ya
        bc = xb * yc - xc * yb
        ex = ab * (ab + ac - 3 * bc) + ac * ac  # /* P0 part of self-intersection loop? */
        if ex > 0:
            f = 1  # /* calc resolution */
        else:
            f = floor(sqrt(1 + 1024 / x1))  # /* calc resolution */
        ab *= f
        ac *= f
        bc *= f
        ex *= f * f  # /* increase resolution */
        xy = 9 * (ab + ac + bc) / 8
        cb = 8 * (xa - ya)  # /* init differences of 1st degree */
        dx = 27 * (8 * ab * (yb * yb - ya * yc) + ex * (ya + 2 * yb + yc)) / 64 - ya * ya * (xy - ya)
        dy = 27 * (8 * ab * (xb * xb - xa * xc) - ex * (xa + 2 * xb + xc)) / 64 - xa * xa * (xy + xa)
        # /* init differences of 2nd degree */
        xx = 3 * (3 * ab * (3 * yb * yb - ya * ya - 2 * ya * yc) - ya * (3 * ac * (ya + yb) + ya * cb)) / 4
        yy = 3 * (3 * ab * (3 * xb * xb - xa * xa - 2 * xa * xc) - xa * (3 * ac * (xa + xb) + xa * cb)) / 4
        xy = xa * ya * (6 * ab + 6 * ac - 3 * bc + cb)
        ac = ya * ya
        cb = xa * xa
        xy = 3 * (xy + 9 * f * (cb * yb * yc - xb * xc * ac) - 18 * xb * yb * ab) / 8

        if ex < 0:  # /* negate values if inside self-intersection loop */
            dx = -dx
            dy = -dy
            xx = -xx
            yy = -yy
            xy = -xy
            ac = -ac
            cb = -cb  # /* init differences of 3rd degree */
        ab = 6 * ya * ac
        ac = -6 * xa * ac
        bc = 6 * ya * cb
        cb = -6 * xa * cb
        dx += xy
        ex = dx + dy
        dy += xy  # /* error of 1st step */
        try:
            pxy = 0
            fx = fy = f
            while x0 != x3 and y0 != y3:
                if leg == 0:
                    second_leg.append((x0, y0, 1))  # /* plot curve */
                else:
                    yield x0, y0, 1  # /* plot curve */
                while True:  # /* move sub-steps of one pixel */
                    if pxy == 0:
                        if dx > xy or dy < xy:
                            raise StopIteration  # /* confusing */
                    if pxy == 1:
                        if dx > 0 or dy < 0:
                            raise StopIteration  # /* values */
                    y1 = 2 * ex - dy  # /* save value for test of y step */
                    if 2 * ex >= dx:  # /* x sub-step */
                        fx -= 1
                        dx += xx
                        ex += dx
                        xy += ac
                        dy += xy
                        yy += bc
                        xx += ab
                    elif y1 > 0:
                        raise StopIteration
                    if y1 <= 0:  # /* y sub-step */
                        fy -= 1
                        dy += yy
                        ex += dy
                        xy += bc
                        dx += xy
                        xx += ac
                        yy += cb
                    if not (fx > 0 and fy > 0):  # /* pixel complete? */
                        break
                if 2 * fx <= f:
                    x0 += sx
                    fx += f  # /* x step */
                if 2 * fy <= f:
                    y0 += sy
                    fy += f  # /* y step */
                if pxy == 0 and dx < 0 and dy > 0:
                    pxy = 1  # /* pixel ahead valid */
        except StopIteration:
            pass
        xx = x0
        x0 = x3
        x3 = xx
        sx = -sx
        xb = -xb  # /* swap legs */
        yy = y0
        y0 = y3
        y3 = yy
        sy = -sy
        yb = -yb
        x1 = x2
        if not (leg != 0):
            break
        leg -= 1  # /* try other end */
    for plot in plot_line(x3, y3, x0, y0):  # /* remaining part in case of cusp or crunode */
        second_leg.append(plot)
    for plot in reversed(second_leg):
        yield plot


def plot_cubic_bezier(x0, y0, x1, y1, x2, y2, x3, y3):
    """plot any cubic Bezier curve"""
    n = 0
    i = 0
    xc = x0 + x1 - x2 - x3
    xa = xc - 4 * (x1 - x2)
    xb = x0 - x1 - x2 + x3
    xd = xb + 4 * (x1 + x2)
    yc = y0 + y1 - y2 - y3
    ya = yc - 4 * (y1 - y2)
    yb = y0 - y1 - y2 + y3
    yd = yb + 4 * (y1 + y2)
    fx0 = x0
    fx1 = 0
    fx2 = 0
    fx3 = 0
    fy0 = y0
    fy1 = 0
    fy2 = 0
    fy3 = 0
    t1 = xb * xb - xa * xc
    t2 = 0
    t = [0] * 5
    # /* sub-divide curve at gradient sign changes */
    if xa == 0:  # /* horizontal */
        if abs(xc) < 2 * abs(xb):
            t[n] = xc / (2.0 * xb)  # /* one change */
            n += 1
    elif t1 > 0.0:  # /* two changes */
        t2 = sqrt(t1)
        t1 = (xb - t2) / xa
        if abs(t1) < 1.0:
            t[n] = t1
            n += 1
        t1 = (xb + t2) / xa
        if abs(t1) < 1.0:
            t[n] = t1
            n += 1
    t1 = yb * yb - ya * yc
    if ya == 0:  # /* vertical */
        if abs(yc) < 2 * abs(yb):
            t[n] = yc / (2.0 * yb)  # /* one change */
            n += 1
    elif t1 > 0.0:  # /* two changes */
        t2 = sqrt(t1)
        t1 = (yb - t2) / ya
        if abs(t1) < 1.0:
            t[n] = t1
            n += 1
        t1 = (yb + t2) / ya
        if abs(t1) < 1.0:
            t[n] = t1
            n += 1
    i = 1
    while i < n:  # /* bubble sort of 4 points */
        t1 = t[i - 1]
        if t1 > t[i]:
            t[i - 1] = t[i]
            t[i] = t1
            i = 0
        i += 1
    t1 = -1.0
    t[n] = 1.0  # /* begin / end point */
    for i in range(0, n + 1):  # /* plot each segment separately */
        t2 = t[i]  # /* sub-divide at t[i-1], t[i] */
        fx1 = (t1 * (t1 * xb - 2 * xc) - t2 * (t1 * (t1 * xa - 2 * xb) + xc) + xd) / 8 - fx0
        fy1 = (t1 * (t1 * yb - 2 * yc) - t2 * (t1 * (t1 * ya - 2 * yb) + yc) + yd) / 8 - fy0
        fx2 = (t2 * (t2 * xb - 2 * xc) - t1 * (t2 * (t2 * xa - 2 * xb) + xc) + xd) / 8 - fx0
        fy2 = (t2 * (t2 * yb - 2 * yc) - t1 * (t2 * (t2 * ya - 2 * yb) + yc) + yd) / 8 - fy0
        fx3 = (t2 * (t2 * (3 * xb - t2 * xa) - 3 * xc) + xd) / 8
        fx0 -= fx3
        fy3 = (t2 * (t2 * (3 * yb - t2 * ya) - 3 * yc) + yd) / 8
        fy0 -= fy3
        x3 = floor(fx3 + 0.5)
        y3 = floor(fy3 + 0.5)  # /* scale bounds */
        if fx0 != 0.0:
            fx0 = (x0 - x3) / fx0
            fx1 *= fx0
            fx2 *= fx0
        if fy0 != 0.0:
            fy0 = (y0 - y3) / fy0
            fy1 *= fy0
            fy2 *= fy0
        if x0 != x3 or y0 != y3:  # /* segment t1 - t2 */
            # plotCubicBezierSeg(x0,y0, x0+fx1,y0+fy1, x0+fx2,y0+fy2, x3,y3)
            for plot in plot_cubic_bezier_seg(x0, y0, x0 + fx1, y0 + fy1, x0 + fx2, y0 + fy2, x3, y3):
                yield plot
        x0 = x3
        y0 = y3
        fx0 = fx3
        fy0 = fy3
        t1 = t2


M_MAX = 6


def plot_quad_spline(n, x, y):
    # /* plot quadratic spline, destroys input arrays x,y */
    mi = 1.0
    m = [0.0] * M_MAX  # /* diagonal constants of matrix */
    i = 0
    x0 = 0
    y0 = 0
    x1 = 0
    y1 = 0
    x2 = x[n]
    y2 = y[n]

    assert (n > 1)  # /* need at least 3 points P[0]..P[n] */

    x[1] = x0 = 8 * x[1] - 2 * x[0]  # /* first row of matrix */
    y[1] = y0 = 8 * y[1] - 2 * y[0]

    for i in range(2, n):  # /* forward sweep */
        if i - 2 < M_MAX:
            m[i - 2] = mi = 1.0 / (6.0 - mi)
        x[i] = x0 = floor(8 * x[i] - x0 * mi + 0.5)  # /* store yi */
        y[i] = y0 = floor(8 * y[i] - y0 * mi + 0.5)
    x1 = floor((x0 - 2 * x2) / (5.0 - mi) + 0.5)  # /* correction last row */
    y1 = floor((y0 - 2 * y2) / (5.0 - mi) + 0.5)

    for i in range(n - 2, -1, -1):  # /* back substitution */
        if i <= M_MAX:
            mi = m[i - 1]
        x0 = floor((x[i] - x1) * mi + 0.5)  # /* next corner */
        y0 = floor((y[i] - y1) * mi + 0.5)
        for plot in plot_quad_bezier((x0 + x1) / 2, (y0 + y1) / 2, x1, y1, x2, y2):
            yield plot
        x2 = (x0 + x1) / 2
        x1 = x0
        y2 = (y0 + y1) / 2
        y1 = y0
    for plot in plot_quad_bezier(x[0], y[0], x1, y1, x2, y2):
        yield plot


def plot_cubic_spline(n, x, y):
    # /* plot cubic spline, destroys input arrays x,y */
    mi = 0.25
    m = [0.0] * M_MAX  # /* diagonal constants of matrix */
    x3 = x[n - 1]
    y3 = y[n - 1]
    x4 = x[n]
    y4 = y[n]
    i = 0
    x0 = 0
    y0 = 0
    x1 = 0
    y1 = 0
    x2 = 0
    y2 = 0

    assert (n > 2)  # /* need at least 4 points P[0]..P[n] */

    x[1] = x0 = 12 * x[1] - 3 * x[0]  # /* first row of matrix */
    y[1] = y0 = 12 * y[1] - 3 * y[0]

    for i in range(2, n):  # /* foreward sweep */
        if i - 2 < M_MAX:
            m[i - 2] = mi = 0.25 / (2.0 - mi)
        x[i] = x0 = floor(12 * x[i] - 2 * x0 * mi + 0.5)
        y[i] = y0 = floor(12 * y[i] - 2 * y0 * mi + 0.5)
    x2 = floor((x0 - 3 * x4) / (7 - 4 * mi) + 0.5)  # /* correct last row */
    y2 = floor((y0 - 3 * y4) / (7 - 4 * mi) + 0.5)
    for plot in plot_cubic_bezier(x3, y3, (x2 + x4) / 2, (y2 + y4) / 2, x4, y4, x4, y4):
        yield plot

    if n - 3 < M_MAX:
        mi = m[n - 3]
    x1 = floor((x[n - 2] - 2 * x2) * mi + 0.5)
    y1 = floor((y[n - 2] - 2 * y2) * mi + 0.5)
    for i in range(n - 3, 0, -1):  # /* back substitution */
        if i <= M_MAX:
            mi = m[i - 1]
        x0 = floor((x[i] - 2 * x1) * mi + 0.5)
        y0 = floor((y[i] - 2 * y1) * mi + 0.5)
        x4 = floor((x0 + 4 * x1 + x2 + 3) / 6.0)  # /* reconstruct P[i] */
        y4 = floor((y0 + 4 * y1 + y2 + 3) / 6.0)
        for plot in plot_cubic_bezier(x4, y4,
                                      floor((2 * x1 + x2) / 3 + 0.5), floor((2 * y1 + y2) / 3 + 0.5),
                                      floor((x1 + 2 * x2) / 3 + 0.5), floor((y1 + 2 * y2) / 3 + 0.5),
                                      x3, y3):
            yield plot
        x3 = x4
        y3 = y4
        x2 = x1
        y2 = y1
        x1 = x0
        y1 = y0
    x0 = x[0]
    x4 = floor((3 * x0 + 7 * x1 + 2 * x2 + 6) / 12.0)  # /* reconstruct P[1] */
    y0 = y[0]
    y4 = floor((3 * y0 + 7 * y1 + 2 * y2 + 6) / 12.0)
    for plot in plot_cubic_bezier(x4, y4, floor((2 * x1 + x2) / 3 + 0.5), floor((2 * y1 + y2) / 3 + 0.5),
                                  floor((x1 + 2 * x2) / 3 + 0.5), floor((y1 + 2 * y2) / 3 + 0.5), x3, y3):
        yield plot
    for plot in plot_cubic_bezier(x0, y0, x0, y0, (x0 + x1) / 2, (y0 + y1) / 2, x4, y4):
        yield plot
