# from copy import copy
# from typing import Any, Optional
#
# from meerk40t.svgelements import Point
#
# TYPE_POINT = 0b00000000_00000000_00000000_00000000
# TYPE_SEGMENT = 0b11000000_00000000_00000000_00000000
# TYPE_AREA = 0b10000000_00000000_00000000_00000000
#
# OFFSET_TYPE = 28
# MASK_HEADER = 0b11110000_00000000_00000000_00000000
# MASK_BODY = 0b00001111_11111111_11111111_11111111
#
# OFFSET_POINT_LAYER = 18
# MASK_POINT_LAYER = 0b00001111_11111100_00000000_00000000  # //1024 layers
# MASK_POINT_INDEX = 0b00000000_00000011_11111111_11111111  # //256k points.
#
# MASK_POS = 0b00010000_00000000_00000000_00000000
# MASK_POS_LO = 0b00010000_00000000_00000000_00000000
# MASK_POS_HI = 0b00000000_00000000_00000000_00000000
#
#
# def refNode(index: int, lo: bool) -> int:
#     return TYPE_AREA | (MASK_POS_LO if lo else 0) | (MASK_BODY & index)
#
#
# def refPoint(layerIndex: int, index: int) -> int:
#     return (
#         TYPE_POINT
#         | (MASK_POINT_LAYER & (layerIndex << OFFSET_POINT_LAYER))
#         | (MASK_POINT_INDEX & index)
#     )
#
#
# def refSegment(layerIndex: int, index: int, lo: bool) -> int:
#     return (
#         TYPE_SEGMENT
#         | (MASK_POS_LO if lo else 0)
#         | (MASK_POINT_LAYER & (layerIndex << OFFSET_POINT_LAYER))
#         | (MASK_POINT_INDEX & index)
#     )
#
#
# class PointsDirect:
#     def __init__(self):
#         pass
#
#
# class Area:
#     """
#     Area is a bound checking AABB data structure which stores within it a series of references
#     to specific points within the area context.
#
#     It maintains the sorting of the x_axis and y_axis data such that it maintains sorted lists in each coordinate
#     direction.
#     """
#
#     def __init__(self, context):
#         self.context = context
#         self.minX = float("inf")
#         self.minY = float("inf")
#         self.maxX = -float("inf")
#         self.maxY = -float("inf")
#         self.x_axis = []
#         self.y_axis = []
#
#     @property
#     def size(self):
#         return len(self.x_axis)
#
#     def set_area(self, b):
#         self.x_axis = copy(b.x_axis)
#         self.y_axis = copy(b.y_axis)
#         self.minX = b.getMinX()
#         self.maxX = b.getMaxX()
#         self.minY = b.getMinY()
#         self.maxY = b.getMaxY()
#         self.context = b.context
#
#     def merge(self, b, ref: int):
#         if self.size == 0:
#             return
#         if ref != -1:
#             index = ref & MASK_BODY
#             self.remove(index, MASK_BODY, b.minX, b.minY)
#             self.remove(index, MASK_BODY, b.maxX, b.maxY)
#         self.mergeX_group(b.x_axis, b.size)
#         self.mergeY_group(b.y_axis, b.size)
#         b.x_axis.clear()
#         b.y_axis.clear()
#
#     def getX(self, i: int) -> float:
#         return self.context.getXref(self.x_axis[i])
#
#     def getY(self, i: int) -> float:
#         return self.context.getYref(self.x_axis[i])
#         # getY uses the same ref as x, to refer to same entity.
#
#     def getMinX(self) -> float:
#         return self.minX
#
#     def getMaxX(self) -> float:
#         return self.maxX
#
#     def getMinY(self) -> float:
#         return self.minY
#
#     def getMaxY(self) -> float:
#         return self.maxY
#
#     def contains(self, x: float, y: float) -> bool:
#         return self.minX <= x <= self.maxX and self.maxY >= y >= self.minY
#
#     def containsX(self, x: float) -> bool:
#         return self.minX <= x <= self.maxX
#
#     def containsY(self, y: float) -> bool:
#         return self.maxY >= y >= self.minY
#
#     def checkBounds(self, px: float, py: float) -> bool:
#         bounds_changed = False
#         if px < self.minX:
#             self.minX = px
#             bounds_changed = True
#         if px > self.maxX:
#             self.maxX = px
#             bounds_changed = True
#         if py < self.minY:
#             self.minY = py
#             bounds_changed = True
#         if py > self.maxY:
#             self.maxY = py
#             bounds_changed = True
#         return bounds_changed
#
#     def addRef(self, refx: int, refy: int = None):
#         if refy is None:
#             refy = refx
#         x = self.context.getXref(refx)
#         y = self.context.getYref(refy)
#         self.checkBounds(x, y)
#         pos_x = self.binarySearchX(x)
#         if pos_x < 0:
#             pos_x = ~pos_x
#         pos_y = self.binarySearchY(y)
#         if pos_y < 0:
#             pos_y = ~pos_y
#         self.x_axis.insert(pos_x, refx)
#         self.y_axis.insert(pos_y, refy)
#
#     def add(self, layerIndex: int, _list: list):
#         for i in range(len(_list)):
#             ref = refPoint(layerIndex, i)
#             self.addRef(ref)
#
#     def compareX(self, a: int, b: int) -> int:
#         v = self.context.getXref(a) - self.context.getXref(b)
#         if v > 0:
#             return 1
#         if v < 0:
#             return -1
#         return 0
#
#     def compareY(self, a: int, b: int) -> int:
#         v = self.context.getYref(a) - self.context.getYref(b)
#         if v > 0:
#             return 1
#         if v < 0:
#             return -1
#         return 0
#
#     def binarySearchX(
#         self, _list: list = None, fromIndex: int = 0, toIndex: int = None, x: float = 0
#     ) -> int:
#         if _list is None:
#             _list = self.x_axis
#             toIndex = len(_list)
#         low = fromIndex
#         high = toIndex - 1
#         while low <= high:
#             mid = (low + high) >> 1
#             midVal = self.context.getXref(_list[mid])
#             v = midVal - x
#             if v < 0:
#                 low = mid + 1
#             elif v > 0:
#                 high = mid - 1
#             else:
#                 return mid  # // key found
#         return -(low + 1)  # // key not found.
#
#     def binarySearchY(
#         self, _list: list = None, fromIndex: int = 0, toIndex: int = None, y: float = 0
#     ) -> int:
#         if _list is None:
#             _list = self.y_axis
#             toIndex = len(_list)
#         low = fromIndex
#         high = toIndex - 1
#         while low <= high:
#             mid = (low + high) >> 1
#             midVal = self.context.getYref(_list[mid])
#             v = midVal - y
#             if v < 0:
#                 low = mid + 1
#             elif v > 0:
#                 high = mid - 1
#             else:
#                 return mid  # // key found
#         return -(low + 1)  # // key not found.
#
#     def gallopSearchX(self, current: int, array: list, v: int) -> int:
#         d = 1
#         seek = current - d
#         prevIteration = seek
#         while seek > 0:
#             if self.compareX(array[seek], v) <= 0:
#                 break
#             prevIteration = seek
#             d <<= 1
#             seek = current - d
#             if seek < 0:
#                 seek = 0
#         if prevIteration != seek:
#             seek = self.binarySearchX(array, seek, prevIteration, v)
#             seek = seek if seek >= 0 else ~seek
#         return seek
#
#     def gallopSearchY(self, current: int, array: list, v: int) -> int:
#         d = 1
#         seek = current - d
#         prevIteration = seek
#         while seek > 0:
#             if self.compareY(array[seek], v) <= 0:
#                 break
#             prevIteration = seek
#             d <<= 1
#             seek = current - d
#             if seek < 0:
#                 seek = 0
#         if prevIteration != seek:
#             seek = self.binarySearchY(array, seek, prevIteration, v)
#             seek = seek if seek >= 0 else ~seek
#         return seek
#
#     def binarySortX(self, a: list, lo: int, hi: int):
#         start = lo + 1
#         while start < hi:
#             pivot = a[start]
#             left = lo
#             right = start
#             while left < right:
#                 mid = (left + right) >> 1
#                 if self.compareX(pivot, a[mid]) < 0:
#                     right = mid
#                 else:
#                     left = mid + 1
#             n = start - left
#             if n == 2:
#                 a[left + 2] = a[left + 1]
#             elif n == 1:
#                 a[left + 2] = a[left + 1]
#                 a[left + 1] = a[left]
#             else:
#                 a[left + 1 : left + 1 + n] = a[left : left + n]
#             a[left] = pivot
#             start += 1
#
#     def binarySortY(self, a: list, lo: int, hi: int):
#         start = lo + 1
#         while start < hi:
#             pivot = a[start]
#             left = lo
#             right = start
#             while left < right:
#                 mid = (left + right) >> 1
#                 if self.compareY(pivot, a[mid]) < 0:
#                     right = mid
#                 else:
#                     left = mid + 1
#             n = start - left
#             if n == 2:
#                 a[left + 2] = a[left + 1]
#             elif n == 1:
#                 a[left + 2] = a[left + 1]
#                 a[left + 1] = a[left]
#             else:
#                 a[left + 1 : left + 1 + n] = a[left : left + n]
#             a[left] = pivot
#             start += 1
#
#     def mergeX_group(self, b: list[int], bsize: int):
#         self.mergeX(self.self.x_axis, self.x_axis, self.size, b, bsize)
#
#     def mergeY_group(self, b: list[int], bsize: int):
#         self.mergeY(self.y_axis, self.y_axis, self.size, b, bsize)
#
#     def mergeX(
#         self, results: list[int], a: list[int], aRead: int, b: list[int], bRead: int
#     ) -> list[int]:
#         """
#         GallopMerge of X.
#         """
#         write = aRead + bRead
#         if (results is None) or (len(results) < write):
#             results = [0] * write
#         if aRead > 0 and bRead > 0:
#             c = self.compareX(a[aRead - 1], b[bRead - 1])
#             while aRead > 0 and bRead > 0:
#                 if c == -1:
#                     gallopPos = self.gallopSearchX(bRead, b, a[aRead - 1])
#                     length = bRead - gallopPos
#                     write -= length
#                     bRead = gallopPos
#                     results[write : write + length] = b[gallopPos : gallopPos + length]
#                     gallopPos -= 1
#                     c = 1
#                 else:
#                     gallopPos = self.gallopSearchX(aRead, a, b[bRead - 1])
#                     length = aRead - gallopPos
#                     write -= length
#                     aRead = gallopPos
#                     results[write : write + length] = a[gallopPos : gallopPos + length]
#                     gallopPos -= 1
#                     c = -1
#         if bRead > 0:
#             if b != results:
#                 results[0:bRead] = b[0:bRead]
#         elif aRead > 0:
#             if a != results:
#                 results[0:aRead] = a[0:aRead]
#         return results
#
#     def mergeY(
#         self, results: list[int], a: list[int], aRead: int, b: list[int], bRead: int
#     ) -> list[int]:
#         """
#         GallopMerge of Y.
#         """
#         write = aRead + bRead
#         if results is None or len(results) < write:
#             results = [0] * write
#         if aRead > 0 and bRead > 0:
#             c = self.compareY(a[aRead - 1], b[bRead - 1])
#             while aRead > 0 and bRead > 0:
#                 if c == -1:
#                     gallopPos = self.gallopSearchY(bRead, b, a[aRead - 1])
#                     length = bRead - gallopPos
#                     write -= length
#                     bRead = gallopPos
#                     results[write : write + length] = b[gallopPos : gallopPos + length]
#                     gallopPos -= 1
#                     c = 1
#                 else:
#                     gallopPos = self.gallopSearchY(aRead, a, b[bRead - 1])
#                     length = aRead - gallopPos
#                     write -= length
#                     aRead = gallopPos
#                     results[write : write + length] = a[gallopPos : gallopPos + length]
#                     gallopPos -= 1
#                     c = -1
#         if bRead > 0:
#             if b != results:
#                 results[0:bRead] = b[0:bRead]
#         elif aRead > 0:
#             if a != results:
#                 results[0:aRead] = a[0:aRead]
#         return results
#
#     def remove(self, v: int, mask: int, vx: float, vy: float):
#         xi = self.binarySearchX(vx)
#         if xi < 0:
#             return
#         yi = self.binarySearchY(vy)
#         if yi < 0:
#             return
#         if (self.x_axis[xi] & mask) == v:
#             del self.x_axis[xi]
#         else:
#             for i in range(1, self.size):
#                 if xi + i <= self.size:
#                     if (self.x_axis[xi + i] & mask) == v:
#                         del self.x_axis[xi + i]
#                         break
#                 if xi - i >= 0:
#                     if (self.x_axis[xi - i] & mask) == v:
#                         del self.x_axis[xi - i]
#         if (self.y_axis[yi] & mask) == v:
#             del self.y_axis[yi]
#         else:
#             for i in range(1, self.size):
#                 if yi + i <= self.size:
#                     if (self.x_axis[yi + i] & mask) == v:
#                         del self.x_axis[yi + i]
#                 if yi - i >= 0:
#                     if (self.x_axis[yi - i] & mask) == v:
#                         del self.x_axis[yi - i]
#
#
# class SeekArea(Area):
#     def __init__(self, context):
#         super().__init__(context)
#         self.area = context
#         self._seek_x = -float("inf")
#         self._seek_y = -float("inf")
#         self._pos_x = -1
#         self._pos_y = -1
#
#     def merge(self, b: Area, ref: int):
#         if b is None:
#             return
#         if len(b) == 0:
#             return
#         Area.merge(self, b, ref)
#         self._pos_x = -1
#         self._pos_y = -1
#         self.seek(self._seek_x, self._seek_y, True)
#
#     def update(self):
#         """
#            /**
#         * Update implies that the underlying points have likely changed.
#         * However, since they won't have changed that much, we can just resort.
#         */
#         """
#         self.binarySortX(self.x_axis, 0, len(self))
#         self.binarySortY(self.y_axis, 0, len(self))
#
#     def add_boxindex(self, boxIndex: int):
#         self.addRef(refNode(boxIndex, False))
#         self.addRef(refNode(boxIndex, True))
#
#     def add(
#         self,
#         layerIndex: int,
#         _list: PointsDirect,
#         start: int = None,
#         length: int = None,
#     ):
#         if start is not None:
#             if length is None:
#                 ref = refPoint(layerIndex, start)
#                 self.addRef(ref)
#             else:
#                 for i in range(start, min(len(_list), start + length)):
#                     ref = refPoint(layerIndex, i)
#                     self.addRef(ref)
#         else:
#             for i in range(0, len(_list)):
#                 ref = refPoint(layerIndex, i)
#                 self.addRef(ref)
#
#     def getXindex(self, index: int):
#         return self.context.getXref(self.x_axis[index])
#
#     def getYindex(self, index: int):
#         return self.context.getYref(self.y_axis[index])
#
#     def requiresBoundsChange(self, x: float = None, y: float = None):
#         if y is None:
#             x = self._seek_x
#             y = self._seek_y
#         try:
#             yTop = self.getXindex(self._pos_y)
#         except IndexError:
#             yTop = -float("inf")
#         if yTop < y:
#             return False
#         try:
#             yBottom = self.getXindex(self._pos_y + 1)
#         except IndexError:
#             yBottom = float("inf")
#         if yBottom > y:
#             return False
#         try:
#             xRight = self.getXindex(self._pos_x + 1)
#         except IndexError:
#             xRight = float("inf")
#         if xRight < x:
#             return False
#         try:
#             xLeft = self.getXindex(self._pos_x)
#         except IndexError:
#             xLeft = -float("inf")
#         return not xLeft > x
#
#     def quickSeek(self, x: float, y: float):
#         self.seek(x, y, True)
#
#     def seek(self, x: float, y: float, quick: bool = False):
#         self._seek_x = x
#         self._seek_y = y
#         if quick or (self._pos_x == -1 and self._pos_y == -1):
#             self._pos_y = self.binarySearchY(y)
#             if self._pos_y < 0:
#                 self._pos_y = ~self._pos_y
#         else:
#             try:
#                 yBottom = self.getYindex(self._pos_y + 1)
#             except IndexError:
#                 yBottom = float("inf")
#             while yBottom < self._seek_y:
#                 self._pos_y += 1
#                 try:
#                     yBottom = self.getYindex(self._pos_y + 1)
#                 except IndexError:
#                     yBottom = float("inf")
#             try:
#                 yTop = self.getYindex(self._pos_y)
#             except IndexError:
#                 yTop = -float("inf")
#             while yTop > self._seek_y:
#                 self._pos_y -= 1
#                 try:
#                     yTop = self.getYindex(self._pos_y)
#                 except IndexError:
#                     yTop = -float("inf")
#         if quick or (self._pos_x == -1 and self._pos_y == -1):
#             self._pos_x = self.binarySearchX(x)
#             if self._pos_x < 0:
#                 self._pos_x = ~self._pos_x
#         else:
#             try:
#                 xRight = self.getXindex(self._pos_x + 1)
#             except IndexError:
#                 xRight = float("inf")
#             while xRight < self._seek_x:
#                 self._pos_x += 1
#                 try:
#                     xRight = self.getXindex(self._pos_x + 1)
#                 except IndexError:
#                     xRight = float("inf")
#             try:
#                 xLeft = self.getXindex(self._pos_x)
#             except IndexError:
#                 xLeft = -float("inf")
#             while xLeft > self._seek_x:
#                 self._pos_x -= 1
#                 try:
#                     xLeft = self.getXindex(self._pos_x)
#                 except IndexError:
#                     xLeft = -float("inf")
#
#     def distSq(self, x, y):
#         d = x - y
#         return d * d
#
#
#     def findNearest(
#         self, finds: list[Point], find: Point, minDistance: float, maxDistance: float
#     ):
#         returnVals = [-1] * len(finds)
#         length = self.findRefNearest(
#             returnVals, find.x, find.y, minDistance, maxDistance
#         )
#         for i in range(len(finds)):
#             f = returnVals[i]
#             finds[i] = self.context.getPoint(f) if (i < length) else None
#
#     def findRefNearest(
#         self,
#         x: float,
#         y: float,
#         minDistance: float,
#         maxDistance: float,
#     ):
#         if self.x_axis is None or self.y_axis is None:
#             return -1
#
#         findingDistanceMaxSq = maxDistance * maxDistance
#         findingDistanceMinSq = minDistance * minDistance
#
#         self.quickSeek(x, y)
#
#         returnVals = []
#
#         itr = 0
#         length = 0
#         xPos = True
#         yPos = True
#         xNeg = True
#         yNeg = True
#         while True:
#             if xPos:
#                 o = self._pos_x + itr
#                 if o >= self.size:
#                     if not xNeg:
#                         break
#                     xPos = False
#                 else:
#
#                     v = self.x_axis[o]
#                     vx = self.context.getXref(v) - x
#                     vx *= vx
#                     if vx > findingDistanceMaxSq:
#                         if not xNeg:
#                             break
#                         xPos = False
#                     vy = y - self.context.getYrefMin(v, y)
#                     vy *= vy
#                     d = vx + vy
#                     if findingDistanceMinSq < d < findingDistanceMaxSq:
#                         if v & MASK_HEADER == TYPE_POINT:
#                             length = self.heapInsert(v, returnVals, length, x, y)
#                             lowestInStack = returnVals[0]
#                             if length == len(returnVals):
#                                 findingDistanceMaxSq = self.distSq(
#                                     self.context.getXref(lowestInStack),
#                                     self.context.getYref(lowestInStack),
#                                     x,
#                                     y,
#                                 )
#                         elif v & MASK_POS == MASK_POS_LO:
#                             b = self.context.getArea(v)
#                             self.merge(b, v)
#             if yPos:
#                 o = self._pos_y + itr
#                 if o >= self.size:
#                     if not yNeg:
#                         break
#                     yPos = False
#                 else:
#                     v = self.y_axis[o]
#                     vy = self.context.getYref(v) - y
#                     vy *= vy
#                     if vy > findingDistanceMaxSq:
#                         if not yNeg:
#                             break
#                         yPos = False
#                     vx = x - self.context.getXrefMin(v, x)
#                     vx *= vx
#                     d = vx + vy
#                     if findingDistanceMinSq < d < findingDistanceMaxSq:
#                         if v & MASK_HEADER == TYPE_POINT:
#                             length = self.heapInsert(v, returnVals, length, x, y)
#                             lowestInStack = returnVals[0]
#                             if length == len(returnVals):
#                                 findingDistanceMaxSq = self.distSq(
#                                     self.context.getXref(lowestInStack),
#                                     self.context.getYref(lowestInStack),
#                                     x,
#                                     y,
#                                 )
#                         elif v & MASK_POS == MASK_POS_LO:
#                             b = self.context.getArea(v)
#                             self.merge(b, v)
#             if xNeg:
#                 o = self._pos_x + ~itr
#                 if o < 0:
#                     if not xPos:
#                         break
#                     xNeg = False
#                 else:
#                     v = self.x_axis[o]
#                     vx = self.context.getXref(v) - x
#                     vx *= vx
#                     if vx > findingDistanceMaxSq:
#                         if not xPos:
#                             break
#                         xNeg = False
#                     vy = y - self.context.getYrefMin(v, y)
#                     vy *= vy
#                     d = vx + vy
#                     if findingDistanceMinSq < d < findingDistanceMaxSq:
#                         if v & MASK_HEADER == TYPE_POINT:
#                             length = self.heapInsert(v, returnVals, length, x, y)
#                             lowestInStack = returnVals[0]
#                             if length == len(returnVals):
#                                 findingDistanceMaxSq = self.distSq(
#                                     self.context.getXref(lowestInStack),
#                                     self.context.getYref(lowestInStack),
#                                     x,
#                                     y,
#                                 )
#                         elif v & MASK_POS == MASK_POS_HI:
#                             b = self.context.getArea(v)
#                             self.merge(b, v)
#             if yNeg:
#                 o = self._pos_y + ~itr
#                 if o < 0:
#                     if not yPos:
#                         break
#                     yNeg = False
#                 else:
#                     v = self.y_axis[o]
#                     vy = self.context.getYref(v) - y
#                     vy *= vy
#                     if vy > findingDistanceMaxSq:
#                         if not yPos:
#                             break
#                         yNeg = False
#                     vx = x - self.context.getXrefMin(v, x)
#                     vx *= vx
#                     d = vx + vy
#                     if findingDistanceMinSq < d < findingDistanceMaxSq:
#                         if v & MASK_HEADER == TYPE_POINT:
#                             length = self.heapInsert(v, returnVals, length, x, y)
#                             lowestInStack = returnVals[0]
#                             if length == len(returnVals):
#                                 findingDistanceMaxSq = self.distSq(
#                                     self.context.getXref(lowestInStack),
#                                     self.context.getYref(lowestInStack),
#                                     x,
#                                     y,
#                                 )
#                         elif v & MASK_POS == MASK_POS_HI:
#                             b = self.context.getArea(v)
#                             self.merge(b, v)
#             itr += 1
#         return length, returnVals
#
#     def heapInsert(self, item: int, heap: list[int], length: int, x: float, y: float):
#         if length == heap.length:
#             # //remove
#             replace = heap[--length]
#             index = 0
#             heap[index] = replace
#
#             # //heapify
#             while (index << 1) + 1 <= length:  # //while children exist.
#                 left = (index << 1) + 1
#                 right = left + 1
#                 childIndex = left
#                 if right <= length:
#                     pointIndex = heap[right]
#                     rightDistance = self.distSq(
#                         self.context.getXref(pointIndex),
#                         self.context.getYref(pointIndex),
#                         x,
#                         y,
#                     )
#                     pointIndex = heap[left]
#                     leftDistance = self.distSq(
#                         self.context.getXref(pointIndex),
#                         self.context.getYref(pointIndex),
#                         x,
#                         y,
#                     )
#                     childIndex = right if rightDistance > leftDistance else left
#                 node = heap[index]
#                 child = heap[childIndex]
#                 nodeDistance = self.distSq(
#                     self.context.getXref(node), self.context.getYref(node), x, y
#                 )
#                 childDistance = self.distSq(
#                     self.context.getXref(child), self.context.getYref(child), x, y
#                 )
#                 if nodeDistance > childDistance:
#                     break
#                 heap[index] = child
#                 heap[childIndex] = node
#                 index = childIndex
#         # //insert
#         index = length
#         heap[index] = item
#         while index != 0:
#             parentIndex = (index - 1) / 2
#             parentItem = heap[parentIndex]
#             parentDistance = self.distSq(
#                 self.context.getXref(parentItem), self.context.getYref(parentItem), x, y
#             )
#             itemDistance = self.distSq(
#                 self.context.getXref(item), self.context.getYref(item), x, y
#             )
#             if itemDistance < parentDistance:
#                 break
#             heap[index] = parentItem
#             heap[parentIndex] = item
#             index = parentIndex
#         length += 1
#         return length
#
#
# class AreaContext:
#     """
#     * An area context stores datapoints and direct references to a list of Points instances in single integers.
#     * The masking is such that it permits 1024 different layers and 256k points within those layers.
#     * The encoded data can reference a specific point, segment or area or a combination of those. For segments,
#     * these can be furthered qualified as the high end or the low end.
#     *
#     * The getXref and getYref takes in a reference integer and provides the data it encodes for.
#     *
#     * The class ultimately provides a very cheap shorthand for referencing data.
#     *
#     * Since areas are defined by their AABB rather than specific points with Points objects, they are stored
#     separately.
#     """
#
#     def __init__(self):
#         self.points = []
#
#     def add(self, _list):
#         self.points.extend(_list)
#
#     def getPoint(self, ref: int) -> Optional[Any]:
#         if ref & MASK_HEADER == TYPE_POINT:
#             return self.points[ref >> OFFSET_POINT_LAYER].getPoint(
#                 ref & MASK_POINT_INDEX
#             )
#         else:
#             return None
#
#     def getXref(self, ref: int) -> float:
#         if ref & MASK_HEADER == TYPE_SEGMENT | MASK_POS_HI:
#             return max(
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                     ((ref & MASK_BODY) & MASK_POINT_INDEX) + 1
#                 ),
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                     (ref & MASK_BODY) & MASK_POINT_INDEX
#                 ),
#             )
#         elif ref & MASK_HEADER == TYPE_SEGMENT | MASK_POS_LO:
#             return min(
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                     ((ref & MASK_BODY) & MASK_POINT_INDEX) + 1
#                 ),
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                     (ref & MASK_BODY) & MASK_POINT_INDEX
#                 ),
#             )
#         elif ref & MASK_HEADER == TYPE_AREA | MASK_POS_LO:
#             return self.areas[ref & MASK_BODY].getMinX()
#         elif ref & MASK_HEADER == TYPE_AREA | MASK_POS_HI:
#             return self.areas[ref & MASK_BODY].getMaxX()
#         else:
#             return self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                 ref & MASK_POINT_INDEX
#             )
#
#     def getXrefMin(self, ref: int, v: float) -> float:
#         if (
#             ref & MASK_HEADER == TYPE_SEGMENT | MASK_POS_LO
#             or ref & MASK_HEADER == TYPE_SEGMENT
#         ):
#             f = min(
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                     ((ref & MASK_BODY) & MASK_POINT_INDEX) + 1
#                 ),
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                     (ref & MASK_BODY) & MASK_POINT_INDEX
#                 ),
#             )  # Two sequential points.
#
#             e = max(
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                     ((ref & MASK_BODY) & MASK_POINT_INDEX) + 1
#                 ),
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                     (ref & MASK_BODY) & MASK_POINT_INDEX
#                 ),
#             )
#             if v < f:
#                 return f
#             if v > e:
#                 return e
#             return v
#         elif (
#             ref & MASK_HEADER == TYPE_AREA
#             or ref & MASK_HEADER == TYPE_AREA | MASK_POS_LO
#         ):
#             b = self.areas[ref & MASK_BODY]
#             f = b.getMinX()
#             e = b.getMaxX()
#             if v < f:
#                 return f
#             if v > e:
#                 return e
#             return v
#         else:
#             return self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getX(
#                 ref & MASK_POINT_INDEX
#             )
#
#     def getYref(self, ref: int) -> float:
#         if ref & MASK_HEADER == TYPE_SEGMENT | MASK_POS_HI:
#             return max(
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#                     ((ref & MASK_BODY) & MASK_POINT_INDEX) + 1
#                 ),
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#                     (ref & MASK_BODY) & MASK_POINT_INDEX
#                 ),
#             )
#         if ref & MASK_HEADER == TYPE_SEGMENT | MASK_POS_LO:
#             return min(
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#                     ((ref & MASK_BODY) & MASK_POINT_INDEX) + 1
#                 ),
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#                     (ref & MASK_BODY) & MASK_POINT_INDEX
#                 ),
#             )
#         if ref & MASK_HEADER == TYPE_AREA | MASK_POS_LO:
#             return self.areas[(ref & MASK_BODY) & MASK_BODY].getMinY()
#         if ref & MASK_HEADER == TYPE_AREA | MASK_POS_HI:
#             return self.areas[(ref & MASK_BODY) & MASK_BODY].getMaxY()
#         return self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#             (ref & MASK_BODY) & MASK_POINT_INDEX
#         )
#
#     def getYrefMin(self, ref: int, v: float) -> float:
#         if (
#             ref & MASK_HEADER == TYPE_SEGMENT | MASK_POS_LO
#             or ref & MASK_HEADER == TYPE_SEGMENT
#         ):
#             f = min(
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#                     ((ref & MASK_BODY) & MASK_POINT_INDEX) + 1
#                 ),
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#                     (ref & MASK_BODY) & MASK_POINT_INDEX
#                 ),
#             )
#             e = max(
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#                     ((ref & MASK_BODY) & MASK_POINT_INDEX) + 1
#                 ),
#                 self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#                     (ref & MASK_BODY) & MASK_POINT_INDEX
#                 ),
#             )
#             if v < f:
#                 return f
#             if v > e:
#                 return e
#             return v
#         elif (
#             ref & MASK_HEADER == TYPE_AREA
#             or ref & MASK_HEADER == TYPE_AREA | MASK_POS_LO
#         ):
#             b = self.areas[ref & MASK_BODY]
#             f = b.getMinY()
#             e = b.getMaxY()
#             if v < f:
#                 return f
#             if v > e:
#                 return e
#             return v
#         return self.points[(ref & MASK_BODY) >> OFFSET_POINT_LAYER].getY(
#             ref & MASK_POINT_INDEX
#         )
