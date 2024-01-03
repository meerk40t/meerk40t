"""
Python implementation of Philip J. Schneider's
"Algorithm for Automatically Fitting Digitized Curves" from the book "Graphics Gems"

Fit one or more cubic Bezier curves to a polyline.

This is a python implementation of Philip J. Schneider's C code. The original C code is
available on http://graphicsgems.org/ as well as in https://github.com/erich666/GraphicsGems

Original code written by Volker Poplawski: https://github.com/volkerp/fitCurves

The python implementation uses NumPy
"""
import numpy as np


# evaluates cubic bezier at t, return point
def bezier_q(ctrlPoly, t):
    return (1.0-t)**3 * ctrlPoly[0] + 3*(1.0-t)**2 * t * ctrlPoly[1] + 3*(1.0-t)* t**2 * ctrlPoly[2] + t**3 * ctrlPoly[3]


# evaluates cubic bezier first derivative at t, return point
def bezier_qprime(ctrlPoly, t):
    return 3*(1.0-t)**2 * (ctrlPoly[1]-ctrlPoly[0]) + 6*(1.0-t) * t * (ctrlPoly[2]-ctrlPoly[1]) + 3*t**2 * (ctrlPoly[3]-ctrlPoly[2])


# evaluates cubic bezier second derivative at t, return point
def bezier_qprimeprime(ctrlPoly, t):
    return 6*(1.0-t) * (ctrlPoly[2]-2*ctrlPoly[1]+ctrlPoly[0]) + 6*(t) * (ctrlPoly[3]-2*ctrlPoly[2]+ctrlPoly[1])


# Fit one (ore more) Bezier curves to a set of points
def fitCurve(points, maxError):
    leftTangent = normalize(points[1] - points[0])
    rightTangent = normalize(points[-2] - points[-1])
    return fitCubic(points, leftTangent, rightTangent, maxError)


def fitCubic(points, leftTangent, rightTangent, error):
    # Use heuristic if region only has two points in it
    if (len(points) == 2):
        dist = np.linalg.norm(points[0] - points[1]) / 3.0
        bezCurve = [points[0], points[0] + leftTangent * dist, points[1] + rightTangent * dist, points[1]]
        return [bezCurve]

    # Parameterize points, and attempt to fit curve
    u = chordLengthParameterize(points)
    bezCurve = generateBezier(points, u, leftTangent, rightTangent)
    # Find max deviation of points to fitted curve
    maxError, splitPoint = computeMaxError(points, bezCurve, u)
    if maxError < error:
        return [bezCurve]

    # If error not too large, try some reparameterization and iteration
    if maxError < error**2:
        for i in range(20):
            uPrime = reparameterize(bezCurve, points, u)
            bezCurve = generateBezier(points, uPrime, leftTangent, rightTangent)
            maxError, splitPoint = computeMaxError(points, bezCurve, uPrime)
            if maxError < error:
                return [bezCurve]
            u = uPrime

    # Fitting failed -- split at max error point and fit recursively
    beziers = []
    centerTangent = normalize(points[splitPoint-1] - points[splitPoint+1])
    beziers += fitCubic(points[:splitPoint+1], leftTangent, centerTangent, error)
    beziers += fitCubic(points[splitPoint:], -centerTangent, rightTangent, error)

    return beziers


def generateBezier(points, parameters, leftTangent, rightTangent):
    bezCurve = [points[0], None, None, points[-1]]

    # compute the A's
    A = np.zeros((len(parameters), 2, 2))
    for i, u in enumerate(parameters):
        A[i][0] = leftTangent  * 3*(1-u)**2 * u
        A[i][1] = rightTangent * 3*(1-u)    * u**2

    # Create the C and X matrices
    C = np.zeros((2, 2))
    X = np.zeros(2)

    for i, (point, u) in enumerate(zip(points, parameters)):
        C[0][0] += np.dot(A[i][0], A[i][0])
        C[0][1] += np.dot(A[i][0], A[i][1])
        C[1][0] += np.dot(A[i][0], A[i][1])
        C[1][1] += np.dot(A[i][1], A[i][1])

        tmp = point - bezier_q([points[0], points[0], points[-1], points[-1]], u)

        X[0] += np.dot(A[i][0], tmp)
        X[1] += np.dot(A[i][1], tmp)

    # Compute the determinants of C and X
    det_C0_C1 = C[0][0] * C[1][1] - C[1][0] * C[0][1]
    det_C0_X  = C[0][0] * X[1] - C[1][0] * X[0]
    det_X_C1  = X[0] * C[1][1] - X[1] * C[0][1]

    # Finally, derive alpha values
    alpha_l = 0.0 if det_C0_C1 == 0 else det_X_C1 / det_C0_C1
    alpha_r = 0.0 if det_C0_C1 == 0 else det_C0_X / det_C0_C1

    # If alpha negative, use the Wu/Barsky heuristic (see text) */
    # (if alpha is 0, you get coincident control points that lead to
    # divide by zero in any subsequent NewtonRaphsonRootFind() call. */
    segLength = np.linalg.norm(points[0] - points[-1])
    epsilon = 1.0e-6 * segLength
    if alpha_l < epsilon or alpha_r < epsilon:
        # fall back on standard (probably inaccurate) formula, and subdivide further if needed.
        bezCurve[1] = bezCurve[0] + leftTangent * (segLength / 3.0)
        bezCurve[2] = bezCurve[3] + rightTangent * (segLength / 3.0)

    else:
        # First and last control points of the Bezier curve are
        # positioned exactly at the first and last data points
        # Control points 1 and 2 are positioned an alpha distance out
        # on the tangent vectors, left and right, respectively
        bezCurve[1] = bezCurve[0] + leftTangent * alpha_l
        bezCurve[2] = bezCurve[3] + rightTangent * alpha_r

    return bezCurve


def reparameterize(bezier, points, parameters):
    return [newtonRaphsonRootFind(bezier, point, u) for point, u in zip(points, parameters)]


def newtonRaphsonRootFind(bez, point, u):
    """
       Newton's root finding algorithm calculates f(x)=0 by reiterating
       x_n+1 = x_n - f(x_n)/f'(x_n)

       We are trying to find curve parameter u for some point p that minimizes
       the distance from that point to the curve. Distance point to curve is d=q(u)-p.
       At minimum distance the point is perpendicular to the curve.
       We are solving
       f = q(u)-p * q'(u) = 0
       with
       f' = q'(u) * q'(u) + q(u)-p * q''(u)

       gives
       u_n+1 = u_n - |q(u_n)-p * q'(u_n)| / |q'(u_n)**2 + q(u_n)-p * q''(u_n)|
    """
    d = bezier_q(bez, u)-point
    numerator = (d * bezier_qprime(bez, u)).sum()
    denominator = (bezier_qprime(bez, u)**2 + d * bezier_qprimeprime(bez, u)).sum()

    if denominator == 0.0:
        return u
    else:
        return u - numerator/denominator


def chordLengthParameterize(points):
    u = [0.0]
    for i in range(1, len(points)):
        u.append(u[i-1] + np.linalg.norm(points[i] - points[i-1]))

    for i, _ in enumerate(u):
        u[i] = u[i] / u[-1]

    return u


def computeMaxError(points, bez, parameters):
    maxDist = 0.0
    splitPoint = len(points)/2
    for i, (point, u) in enumerate(zip(points, parameters)):
        dist = np.linalg.norm(bezier_q(bez, u)-point)**2
        if dist > maxDist:
            maxDist = dist
            splitPoint = i

    return maxDist, splitPoint

def normalize(v):
    return v / np.linalg.norm(v)

"""
Simplify polyline by applying the Ramer-Douglas-Peucker algorithm
"""
def _compute_distances(points, start, end):
    """Compute the distances between all points and the line defined by start and end.

    :param points: Points to compute distance for.
    :param start: Starting point of the line
    :param end: End point of the line

    :return: Points distance to the line.
    """
    line = end - start
    if (line_length := np.linalg.norm(line)) == 0:
        return np.linalg.norm(points - start, axis=-1)
    if line.size == 2:
        return abs(np.cross(line, start - points)) / line_length  # 2D case
    return (
        abs(np.linalg.norm(np.cross(line, start - points), axis=-1)) / line_length
    )  # 3D case


def _mask(points, epsilon: float):
    stack = [[0, len(points) - 1]]
    indices = np.ones(len(points), dtype=bool)

    while stack:
        start_index, last_index = stack.pop()

        local_points = points[indices][start_index + 1 : last_index]
        if len(local_points) == 0:
            continue
        distances = _compute_distances(
            local_points, points[start_index], points[last_index]
        )
        dist_max = max(distances)
        index_max = start_index + 1 + np.argmax(distances)

        if dist_max > epsilon:
            stack.append([start_index, index_max])
            stack.append([index_max, last_index])
        else:
            indices[start_index + 1 : last_index] = False
    return indices


def _rdp(points, epsilon: float):
    """
    Mask will be a list of boolean flags that indicate
    whether a point remains or could be ignored
    points[mask] is then a shortened list:
    points:
        [[129005.90551181 206409.4488189 ]
        [335415.35433071 206409.4488189 ]
        [516023.62204724 206409.4488189 ]
        [696631.88976378 206409.4488189 ]]
    mask:
        [ True False False  True]
    points[mask]:
        [[129005.90551181 206409.4488189 ]
        [696631.88976378 206409.4488189 ]]
    """
    mask = _mask(points, epsilon)
    return points[mask]


def rdp(points, epsilon: float):
    """
    Simplifies a list or an array of points using
    the Ramer-Douglas-Peucker algorithm.
    https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm

    :param points: Array of points (Nx2)
    :param epsilon: epsilon in the rdp algorithm

    :return: Simplified array of points
    """
    if not isinstance(points, np.ndarray):
        return _rdp(np.array(points), epsilon)
    return _rdp(points, epsilon)
