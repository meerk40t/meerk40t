from math import ceil, cos, floor, sin, sqrt, tan

from ..svgelements import Point

try:
    from math import tau
except ImportError:
    from math import pi

    tau = pi * 2

"""
The Zingl-Bresenham plotting algorithms are from Alois Zingl's "The Beauty of Bresenham's Algorithm"
( http://members.chello.at/easyfilter/bresenham.html ).

In the case of Zingl's work this isn't explicit from his website, however from personal
correspondence "'Free and open source' means you can do anything with it like the MIT licence."

The Zingl-Bresenham algorithms are provided in a static fashion and generate x and y locations.

This work is MIT Licensed.
"""


class ZinglPlotter:
    @staticmethod
    def plot_arc(arc):
        """
        Plots an arc by converting it into a series of cubic bezier curves and plotting those instead.

        :param arc:
        :return:
        """
        # TODO: Should actually plot the arc according to the pixel-perfect standard.
        # TODO: In this case we would plot a Bernstein weighted bezier curve.
        sweep_limit = tau / 12
        arc_required = int(ceil(abs(arc.sweep) / sweep_limit))
        if arc_required == 0:
            return
        slice = arc.sweep / float(arc_required)

        theta = arc.get_rotation()
        rx = arc.rx
        ry = arc.ry
        p_start = arc.start
        current_t = arc.get_start_t()
        x0 = arc.center[0]
        y0 = arc.center[1]
        cos_theta = cos(theta)
        sin_theta = sin(theta)

        for i in range(0, arc_required):
            next_t = current_t + slice

            alpha = sin(slice) * (sqrt(4 + 3 * pow(tan((slice) / 2.0), 2)) - 1) / 3.0

            cos_start_t = cos(current_t)
            sin_start_t = sin(current_t)

            ePrimen1x = -rx * cos_theta * sin_start_t - ry * sin_theta * cos_start_t
            ePrimen1y = -rx * sin_theta * sin_start_t + ry * cos_theta * cos_start_t

            cos_end_t = cos(next_t)
            sin_end_t = sin(next_t)

            p2En2x = x0 + rx * cos_end_t * cos_theta - ry * sin_end_t * sin_theta
            p2En2y = y0 + rx * cos_end_t * sin_theta + ry * sin_end_t * cos_theta
            p_end = (p2En2x, p2En2y)
            if i == arc_required - 1:
                p_end = arc.end

            ePrimen2x = -rx * cos_theta * sin_end_t - ry * sin_theta * cos_end_t
            ePrimen2y = -rx * sin_theta * sin_end_t + ry * cos_theta * cos_end_t

            p_c1 = (p_start[0] + alpha * ePrimen1x, p_start[1] + alpha * ePrimen1y)
            p_c2 = (p_end[0] - alpha * ePrimen2x, p_end[1] - alpha * ePrimen2y)

            for value in ZinglPlotter.plot_cubic_bezier(
                p_start[0],
                p_start[1],
                p_c1[0],
                p_c1[1],
                p_c2[0],
                p_c2[1],
                p_end[0],
                p_end[1],
            ):
                yield value
            p_start = Point(p_end)
            current_t = next_t

    @staticmethod
    def plot_line(x0, y0, x1, y1):
        """
        Zingl-Bresenham line draw algorithm

        yields x, y
        """
        x0 = int(x0)
        y0 = int(y0)
        x1 = int(x1)
        y1 = int(y1)
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
            yield x0, y0
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:  # e_xy+e_y < 0
                err += dy
                x0 += sx
            if e2 <= dx:  # e_xy+e_y < 0
                err += dx
                y0 += sy

    @staticmethod
    def plot_quad_bezier_seg(x0, y0, x1, y1, x2, y2):
        """plot a limited quadratic Bezier segment

        This algorithm can plot curves that do not inflect.

        This is used as part of the general algorithm, which breaks at the inflection point.

        yields x, y
        """
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

        assert xx * sx <= 0 and yy * sy <= 0  # /* sign of gradient must not change */

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
                    yield int(x0), int(y0)  # /* plot curve */
                else:
                    points.append((int(x0), int(y0)))
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
                if not (dy < 0 < dx):  # /* gradient negates -> algorithm fails */
                    break
        for plot in ZinglPlotter.plot_line(
            x0, y0, x2, y2
        ):  # /* plot remaining part to end */:
            if points is None:
                yield plot  # /* plot curve */
            else:
                points.append(
                    plot
                )  # plotLine(x0,y0, x2,y2) #/* plot remaining part to end */
        if points is not None:
            for plot in reversed(points):
                yield plot

    @staticmethod
    def plot_quad_bezier(x0, y0, x1, y1, x2, y2):
        """
        Zingl-Bresenham quad bezier draw algorithm.

        Plot any quadratic Bezier curve

        yields x, y
        """

        x0 = int(x0)
        y0 = int(y0)
        # control points are permitted fractional elements.
        x2 = int(x2)
        y2 = int(y2)
        x = x0 - x1
        y = y0 - y1
        t = x0 - 2 * x1 + x2
        r = 0
        points = None

        if x * (x2 - x1) > 0:  # /* horizontal cut at P4? */
            if y * (y2 - y1) > 0:  # /* vertical cut at P6 too? */
                if abs((y0 - 2 * y1 + y2) / t * x) > abs(y):  # /* which first? */
                    x0 = x2
                    x2 = x + x1
                    y0 = y2
                    y2 = y + y1  # /* swap points */
                    points = []
                    # /* now horizontal cut at P4 comes first */
            t = (x0 - x1) / t
            r = (1 - t) * ((1 - t) * y0 + 2.0 * t * y1) + t * t * y2  # /* By(t=P4) */
            t = (x0 * x2 - x1 * x1) * t / (x0 - x1)  # /* gradient dP4/dx=0 */
            x = floor(t + 0.5)
            y = floor(r + 0.5)
            r = (y1 - y0) * (t - x0) / (x1 - x0) + y0  # /* intersect P3 | P0 P1 */
            for plot in ZinglPlotter.plot_quad_bezier_seg(
                x0, y0, x, floor(r + 0.5), x, y
            ):
                if points is None:
                    yield plot
                else:
                    points.append(plot)
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
            for plot in ZinglPlotter.plot_quad_bezier_seg(
                x0, y0, floor(r + 0.5), y, x, y
            ):
                if points is None:
                    yield plot
                else:
                    points.append(plot)
            r = (x1 - x2) * (t - y2) / (y1 - y2) + x2  # /* intersect P7 | P1 P2 */
            x0 = x
            x1 = floor(r + 0.5)
            y0 = y1 = y  # /* P0 = P6, P1 = P7 */
        for plot in ZinglPlotter.plot_quad_bezier_seg(
            x0, y0, x1, y1, x2, y2
        ):  # /* remaining part */
            if points is None:
                yield plot
            else:
                points.append(plot)
        if points is not None:
            for plot in reversed(points):
                yield plot

    @staticmethod
    def plot_cubic_bezier_seg(x0, y0, x1, y1, x2, y2, x3, y3):
        """
        Plot limited cubic Bezier segment

        This algorithm can plot curves that do not inflect.

        It is used as part of the general algorithm, which breaks at the infection point(s)

        yields x, y
        """
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

            for plot in ZinglPlotter.plot_quad_bezier_seg(x0, y0, sx, sy, x3, y3):
                yield plot
            return
        x1 = (x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0) + 1  # /* line lengths */
        x2 = (x2 - x3) * (x2 - x3) + (y2 - y3) * (y2 - y3) + 1

        while True:  # /* loop over both ends */
            ab = xa * yb - xb * ya
            ac = xa * yc - xc * ya
            bc = xb * yc - xc * yb
            ex = (
                ab * (ab + ac - 3 * bc) + ac * ac
            )  # /* P0 part of self-intersection loop? */
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
            dx = 27 * (
                8 * ab * (yb * yb - ya * yc) + ex * (ya + 2 * yb + yc)
            ) / 64 - ya * ya * (xy - ya)
            dy = 27 * (
                8 * ab * (xb * xb - xa * xc) - ex * (xa + 2 * xb + xc)
            ) / 64 - xa * xa * (xy + xa)
            # /* init differences of 2nd degree */
            xx = (
                3
                * (
                    3 * ab * (3 * yb * yb - ya * ya - 2 * ya * yc)
                    - ya * (3 * ac * (ya + yb) + ya * cb)
                )
                / 4
            )
            yy = (
                3
                * (
                    3 * ab * (3 * xb * xb - xa * xa - 2 * xa * xc)
                    - xa * (3 * ac * (xa + xb) + xa * cb)
                )
                / 4
            )
            xy = xa * ya * (6 * ab + 6 * ac - 3 * bc + cb)
            ac = ya * ya
            cb = xa * xa
            xy = (
                3 * (xy + 9 * f * (cb * yb * yc - xb * xc * ac) - 18 * xb * yb * ab) / 8
            )

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
                        second_leg.append((x0, y0))  # /* plot curve */
                    else:
                        yield x0, y0  # /* plot curve */
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
        for plot in ZinglPlotter.plot_line(
            x3, y3, x0, y0
        ):  # /* remaining part in case of cusp or crunode */
            second_leg.append(plot)
        for plot in reversed(second_leg):
            yield plot

    @staticmethod
    def plot_cubic_bezier(x0, y0, x1, y1, x2, y2, x3, y3):
        """
        Zingl-Bresenham cubic bezier draw algorithm

        Plot any quadratic Bezier curve

        yields x, y
        """
        x0 = int(x0)
        y0 = int(y0)
        # control points are permitted fractional elements.
        x3 = int(x3)
        y3 = int(y3)
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
            fx1 = (
                t1 * (t1 * xb - 2 * xc) - t2 * (t1 * (t1 * xa - 2 * xb) + xc) + xd
            ) / 8 - fx0
            fy1 = (
                t1 * (t1 * yb - 2 * yc) - t2 * (t1 * (t1 * ya - 2 * yb) + yc) + yd
            ) / 8 - fy0
            fx2 = (
                t2 * (t2 * xb - 2 * xc) - t1 * (t2 * (t2 * xa - 2 * xb) + xc) + xd
            ) / 8 - fx0
            fy2 = (
                t2 * (t2 * yb - 2 * yc) - t1 * (t2 * (t2 * ya - 2 * yb) + yc) + yd
            ) / 8 - fy0
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
                for plot in ZinglPlotter.plot_cubic_bezier_seg(
                    x0, y0, x0 + fx1, y0 + fy1, x0 + fx2, y0 + fy2, x3, y3
                ):
                    yield plot
            x0 = x3
            y0 = y3
            fx0 = fx3
            fy0 = fy3
            t1 = t2
