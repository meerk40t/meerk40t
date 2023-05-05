"""
This module provides routines to create an offsetted path
"""
from copy import copy
from math import tau
from meerk40t.svgelements import Path, Line, Arc, CubicBezier, QuadraticBezier, Point, Move, Close


class OffsetPath:
    def __init__(self, originalpath=None, offset=0.0, connection=0, **kwds):
        self._offset = offset
        # Connection type:
        # 0: simple line
        # 1: cubic bezier
        self._connection = connection
        self._path = originalpath
        self._cached_result = None

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        if self._offset != value:
            self._offset = value
            del self._cached_result
            self._cached_result = None
            if self._offset == 0:
                self._cached_result = copy(self._path)

    @property
    def connection(self):
        return self._connection

    @connection.setter
    def connection(self, value):
        if self._connection != value:
            self._connection = value
            del self._cached_result
            self._cached_result = None
            if self._offset == 0:
                self._cached_result = copy(self._path)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = copy(value)
        del self._cached_result
        self._cached_result = None
        if self._offset == 0:
            self._cached_result = copy(self._path)

    def calculate_offset(self):

        def normal_to(p1, p2, dist):
            # Establishes the normal to the line between p1 and p2, based on p1
            # and returns the point on that normal with distance dist to p1
            if p1 == p2:
                return Point(x=p1.x, y=p1.y)
            angle = p1.angle_to(p2)
            angle -= tau / 4
            return Point.polar(p1, angle, dist)

        self._cached_result = copy(self._path)
        # We iterate backwards
        # Any single point on the segment will be offset by the offset
        # value perpendicular to the connection line between start and end
        spath = self._cached_result
        lastpoint = None
        continuous = False
        for idx in range(len(spath) - 1, -1, -1):
            seg = spath[idx]
            if isinstance(seg, Arc):
                # This still has flaws!
                print (f"Extended Arc: {seg.__repr__()}")
                continuous = True
                center = seg.center
                # Lets extend start and end
                angle = center.angle_to(seg.start)
                distance = center.distance_to(seg.start)
                seg.start = Point.polar(center, angle, distance + self._offset)
                angle = center.angle_to(seg.end)
                distance = center.distance_to(seg.end)
                seg.end = Point.polar(center, angle, distance + self._offset)
            elif isinstance(seg, CubicBezier):
                continuous = True
                delta = normal_to(seg.start, seg.end, self._offset)
                delta -= seg.start
                print (f"Extended cubic by: {delta}")
                seg.start += delta
                seg.end += delta
                seg.control1 += delta
                seg.control2 += delta
            elif isinstance(seg, QuadraticBezier):
                continuous = True
                delta = normal_to(seg.start, seg.end, self._offset)
                delta -= seg.start
                print (f"Extended quad by: {delta}")
                seg.start += delta
                seg.end += delta
                seg.control += delta
            elif isinstance(seg, Line):
                print(f"Line started with ({seg.start.x:.0f}, {seg.start.y:.0f})-({seg.end.x:.0f}, {seg.end.y:.0f})")
                continuous = True
                delta = normal_to(seg.start, seg.end, self._offset)
                delta -= seg.start
                print (f"Extended line by: {delta}")
                seg.start += delta
                seg.end += delta
                print(f"Line ended with ({seg.start.x:.0f}, {seg.start.y:.0f})-({seg.end.x:.0f}, {seg.end.y:.0f})")
            elif isinstance(seg, Move):
                if lastpoint is not None:
                    seg.end = lastpoint
                continuous = False
            else:
                continuous = False
                print(f"Skipped {type(seg).__name__}")
            # We create an additional connection segment
            # between two segments based on the connection type
            if lastpoint is not None and continuous:
                if seg.end.x != lastpoint.x or seg.end.y != lastpoint.y:
                    if self._connection == 0:  # Simple line
                        connectseg = Line(start=Point(seg.end.x, seg.end.y), end=Point(lastpoint.x, lastpoint.y))
                        print ("Adding line connector")
                    elif self._connection == 1:  # Cubic Bezier
                        c1 = Point(x=seg.end.x, y=seg.end.y)
                        c2 = Point(x=lastpoint.x, y=lastpoint.y)
                        connectseg = CubicBezier(
                            start=Point(seg.end.x, seg.end.y),
                            control1=c1,
                            control2=c2,
                            end=Point(lastpoint.x, lastpoint.y),
                        )
                        print ("Adding cubic connector")
                    else:
                        connectseg = None
                    if connectseg is not None:
                        # Insert it...
                        spath.insert(idx + 1, connectseg)

            lastpoint = seg.start

        self._cached_result.validate_connections()

    def result(self):
        if self._cached_result is None:
            # Calculate
            self.calculate_offset()
        return self._cached_result
