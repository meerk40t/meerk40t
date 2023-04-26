"""
This module provides routines to create an offsetted path
"""
from copy import copy
from meerk40t.svgelements import Path, Line, Arc, CubicBezier, QuadraticBezier, Point


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
        self._cached_result = copy(self._path)
        # We iterate backwards
        # Any single point on the segment will be offset by the offset
        # value perpendicular to the connection line between start and end
        for subpath in self._cached_result.as_subpaths():
            lastpoint = None
            for seg in subpath:
                # Is the index not the last?

                # Then we create an additional connection segment
                # between two segments based on the connection type
                if lastpoint is not None:
                    if seg.end != lastpoint:
                        if self._connection == 0:  # Simple line
                            connectseg = Line(start=copy(seg.end), end=copy(lastpoint))
                        elif self._connection == 1:  # Cubic Bezier
                            c1 = Point(x=seg.end.x, y=seg.end.y)
                            c2 = Point(x=lastpoint.x, y=lastpoint.y)
                            connectseg = CubicBezier(
                                start=copy(seg.end),
                                control1=c1,
                                control2=c2,
                                end=copy(lastpoint),
                            )
                        else:
                            connectseg = None
                        if connectseg is not None:
                            # Insert it...
                            pass

                lastpoint = seg.start

        self._cached_result.validate_connections()

    def result(self):
        if self._cached_result is None:
            # Calculate
            self.calculate_offset()
        return self._cached_result
