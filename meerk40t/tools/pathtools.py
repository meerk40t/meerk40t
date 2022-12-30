from math import isinf, isnan

from meerk40t.svgelements import Point


class GraphNode(Point):
    """
    GraphNodes are nodes within the graph that store a list of connections between points.
    """

    def __init__(self, x, y=None):
        Point.__init__(self, x, y)
        self.connections = []
        self.visited = 0
        self.value = None


class Segment:
    """
    Graphing segments are connections between nodes on the graph that store, their start and end nodes, active state
    for use within the monotonic vector filling. The type of segment it is. The index of the segment around the closed
    shape. A list of bisectors (to calculate the rung attachments).
    """

    def __init__(self, a, b, index=0):
        self.visited = 0
        self.a = a
        self.b = b
        self.active = False
        self.value = "RUNG"
        self.index = index
        self.bisectors = []
        self.object = None

    def __len__(self):
        # [False, i, p0, p1, high, low, m, b, path]
        return 9

    def __str__(self):
        return f"Segment({str(self.a)},{str(self.b)},{str(self.index)},type='{self.value}')"

    def __getitem__(self, item):
        if item == 0:
            return self.active
        if item == 1:
            return self.index
        if item == 2:
            return self.a
        if item == 3:
            return self.b
        if item == 4:
            if self.a.y > self.b.y:
                return self.a
            else:
                return self.b
        if item == 5:
            if self.a.y < self.b.y:
                return self.a
            else:
                return self.b
        if item == 6:
            if self.b[0] - self.a[0] == 0:
                return float("inf")
            return (self.b[1] - self.a[1]) / (self.b[0] - self.a[0])
        if item == 7:
            if self.b[0] - self.a[0] == 0:
                return float("inf")
            im = (self.b[1] - self.a[1]) / (self.b[0] - self.a[0])
            return self.a[1] - (im * self.a[0])
        if item == 8:
            return self.object

    def intersect(self, segment):
        return Segment.line_intersect(
            self.a[0],
            self.a[1],
            self.b[0],
            self.b[1],
            segment.a[0],
            segment.a[1],
            segment.b[0],
            segment.b[1],
        )

    def sort_bisectors(self):
        def distance(a):
            return self.a.distance_to(a)

        self.bisectors.sort(key=distance)

    def get_intercept(self, y):
        im = (self.b[1] - self.a[1]) / (self.b[0] - self.a[0])
        ib = self.a[1] - (im * self.a[0])
        if isnan(im) or isinf(im):
            return self.a[0]
        return (y - ib) / im

    @staticmethod
    def line_intersect(x1, y1, x2, y2, x3, y3, x4, y4):
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        if denom == 0:
            return None  # Parallel.
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
        if 0.0 <= ua <= 1.0 and 0.0 <= ub <= 1.0:
            return (x1 + ua * (x2 - x1)), (y1 + ua * (y2 - y1))
        return None


class Graph:
    """
    A graph is a set of nodes and their connections. The nodes are points within 2d space and any number of segments
    can connect any number of points. There is no order established by the graph. And for our uses here all graphs will
    end up not only being Eulerian but Euloopian. All nodes should have even numbers of connecting segments so that any
    walk will always return to the end location.

    """

    def __init__(self):
        self.nodes = []
        self.links = []

    def add_shape(self, series, close=True):
        """
        Adds a closed shape point series to the graph in a single connected vertex path.
        """
        first_node = None
        last_node = None
        for i in range(len(series)):
            m = series[i]
            current_node = self.new_node(m)
            if i == 0:
                first_node = current_node
            if last_node is not None:
                segment = self.link(last_node, current_node)
                segment.index = i
                segment.value = "EDGE"
            last_node = current_node
        if close:
            segment = self.link(last_node, first_node)
            segment.index = len(series)
            segment.value = "EDGE"

    @staticmethod
    def monotone_fill(graph, outlines, min, max, distance):
        """
        Find all line segments that intersect with the graph segments in the shape outlines. Add the links from right to
        left side of the intersected paths. Add the bisectors to the segments that are bisected.

        Sort all the bisectors and create a graph of monotone rungs and the edges that connect those rungs. Use this
        graph rather than original outline graph used to find the intersections.

        Adds into graph, a graph of all monotone rungs, and the path of edge nodes that connected those intersections.
        """
        crawler = VectorMontonizer(low_value=min, high_value=max, start=min)
        for outline in outlines:
            crawler.add_segment_events(outline.links)
        itr = 0
        while crawler.current_is_valid_range():
            crawler.scanline_increment(distance)
            y = crawler.scanline
            actives = crawler.actives()
            for i in range(1, len(actives), 2):
                left_segment = actives[i - 1]
                right_segment = actives[i]
                left_segment_x = crawler.intercept(left_segment)
                right_segment_x = crawler.intercept(right_segment)
                left_node = graph.new_node((left_segment_x, y))
                right_node = graph.new_node((right_segment_x, y))
                row = graph.link(left_node, right_node)
                row.value = "RUNG"
                row.index = itr
                left_segment.bisectors.append(left_node)
                right_segment.bisectors.append(right_node)
            itr += 1
        for outline in outlines:
            itr = 0
            previous = None
            first = None
            for i in range(len(outline.links)):
                s = outline.links[i]
                if len(s.bisectors) == 0:
                    continue
                s.sort_bisectors()
                for bi in s.bisectors:
                    if previous is not None:
                        segment = graph.link(previous, bi)
                        segment.value = "EDGE"
                        segment.index = itr
                        itr += 1
                    else:
                        first = bi
                    previous = bi
                s.bisectors.clear()
            if previous is not None and first is not None:
                segment = graph.link(previous, first)
                segment.value = "EDGE"
                segment.index = itr

    def new_node(self, point):
        """
        Create and add a new node to the graph at the given point.
        """
        g = GraphNode(point)
        self.nodes.append(g)
        return g

    def new_edge(self, a, b):
        """
        Create an edge connection between a and b.
        """
        s = Segment(a, b)
        self.links.append(s)
        return s

    def detach(self, segment):
        """
        Remove the segment and links from the graph.
        """
        self.links.remove(segment)
        segment.a.connections.remove(segment)
        segment.b.connections.remove(segment)

    def link(self, a, b):
        """
        Creates a new edge linking the points a and be and adds the newly created link to the graph.
        """
        segment = self.new_edge(a, b)
        segment.a.connections.append(segment)
        segment.b.connections.append(segment)
        return segment

    def double(self):
        """
        Makes any graph Eulerian. Any graph that is doubled is by definition Eulerian.

        This is not used by the algorithm.
        @return:
        """
        for i in range(len(self.links)):
            s = self.links[i]
            second_copy = self.link(s.a, s.b)
            if s.value == "RUNG":
                second_copy.value = "SCAFFOLD_RUNG"
            else:
                second_copy.value = "SCAFFOLD"
            second_copy.index = None

    def double_odd_edge(self):
        """
        Makes any outline path an Eularian path, by doubling every other edge. As each node connects with 1 rung, and
        two edges this will double 1 of those edges in every instance, giving a total of 4 connections. This is makes
        the graph Eulerian.

        @return:
        """
        for i in range(len(self.links)):
            segment = self.links[i]
            if segment.value == "EDGE" and segment.index & 1:
                second_copy = self.link(segment.a, segment.b)
                second_copy.value = "SCAFFOLD"
                second_copy.index = None

    def walk(self, points):
        """
        We have an Eulerian graph we must walk through the graph in any direction. This results in a point series that
        will cross every segment once.

        Some segments are marked scaffolding or classes of edge that are not necessary. These are removed for parsimony.

        """
        if len(self.nodes) == 0:
            return
        walker = GraphWalker(self)
        walker.make_walk()
        walker.clip_scaffold_ends()
        walker.clip_scaffold_loops()
        walker.add_walk(points)
        return points

    def is_eulerian(self):
        ends = 0
        for n in self.nodes:
            if len(n.connections) & 1:
                ends += 1
                if ends > 2:
                    return False
        return True

    def is_euloopian(self):
        for n in self.nodes:
            if len(n.connections) & 1:
                return False
        return True


class GraphWalker:
    """
    Graph Walker takes a graph object and finds walks within it.

    If the graph is discontinuous it will find no segment between these elements and add a None segment between them.
    """

    def __init__(self, graph):
        self.graph = graph
        self.walk = list()
        self.flip_start = None
        self.flip_end = None

    def other_node_for_segment(self, current_node, next_segment):
        """
        Segments have two nodes, this finds the other side of the given segment.
        """
        if current_node is next_segment.a:
            return next_segment.b
        else:
            return next_segment.a

    def reset_visited(self):
        for e in self.walk:
            if e is None:
                continue
            e.visited = 0

    def make_walk(self):
        """
        Create the walk out of the current graph. Picks any start point and begins. Note if there
        are odd node elements anywhere
        """
        itr = 0
        for g in self.graph.nodes:
            if not g.visited:
                if itr != 0:
                    self.walk.append(None)  # Segment is None. There is no link here.
                self.make_walk_node(g)
                itr += 1

    def make_walk_node(self, g):
        """
        Starting from the given start node it makes a complete walk in an Eulerian circuit.

        It adds the first loop from the start node, then walks its looped walk adding
        any additional loops it finds to the current loop.
        @param g:
        @return:
        """
        start = len(self.walk)
        self.walk.append(g)
        self.add_loop(start, g)

        i = start
        while i < len(self.walk):
            node = self.walk[i]
            unused = self.find_unused_connection(node)
            if unused is None:
                i += 2
                continue
            self.add_loop(i, node)
            # i += 2

    def add_loop(self, index, node):
        """
        Adds a loop from the current graph node, without revisiting any nodes.
        Returns the altered index caused by adding that loop.

        Travels along unused connections until no more travel is possible. If properly Eulerian,
        this will only happen when it is looped back on itself.

        @param index: index we are adding loop to.
        @param node: Node to find alternative path through.
        @return: new index after loop is added to the walk.
        """
        index += 1
        i = index
        while True:
            node.visited += 1
            unused = self.find_unused_connection(node)
            if unused is None:
                break
            segment = node.connections[unused]
            self.walk.insert(i, segment)
            i += 1
            segment.visited += 1
            node = self.other_node_for_segment(node, segment)
            self.walk.insert(i, node)
            i += 1
        return i - index

    def find_unused_connection(self, node):
        """
        Finds the first unused edge segment within the graph node, or None if all connections are used.

        @param node: Node to find unused edge segment within.
        @return: index of node connection within the graphnode
        """
        value = None
        for index, c in enumerate(node.connections):
            if not c.visited:
                if value is None:
                    value = index
                if c.value == "RUNG":
                    return index
        return value

    def add_walk(self, points):
        """
        Adds nodes within the walk to the points given to it.

        @param points:
        @return:
        """
        for i in range(0, len(self.walk), 2):
            segment = self.walk[i - 1]
            # The first time segment will be the last value (a node) which will set value to none. This is fine.
            point = self.walk[i]
            if segment is None:
                points.append(None)
            else:
                point.value = (
                    segment.value
                )  # This doesn't work, nodes are repeated, so they can't store unique values.
            points.append(point)

    def remove_loop(self, from_pos, to_pos):
        """
        Removes values between the two given points.
        Since start and end are the same node, it leaves one in place.

        @param from_pos:
        @param to_pos:
        @return:
        """
        if from_pos == to_pos:
            return 0
        min_pos = min(from_pos, to_pos)
        max_pos = max(from_pos, to_pos)
        del self.walk[min_pos:max_pos]
        return max_pos - min_pos

    def remove_biggest_loop_in_range(self, start, end):
        """
        Checks scaffolding walk for loops, and removes them if detected.

        It resets the visited values for the scaffold walk.
        It iterates from the outside to the center, setting the visited value for each node.

        If it finds a marked node, that is the biggest loop within the given walk.
        @param start:
        @param end:
        @return:
        """
        for i in range(start, end + 2, 2):
            n = self.get_node(i)
            n.visited = None
        for i in range(0, int((end - start) // 2), 2):
            left = start + i
            right = end - i
            s = self.get_node(left)
            if s.visited is not None:
                return self.remove_loop(left, s.visited)
                # Loop Detected.
            if left == right:
                break
            s.visited = left
            e = self.get_node(right)
            if e.visited is not None:
                return self.remove_loop(right, e.visited)
                # Loop Detected.
            e.visited = right
        return 0

    def clip_scaffold_loops(self):
        """
        Removes loops consisting of scaffolding from the walk.

        Clips unneeded scaffolding.

        @return:
        """
        start = 0
        index = 0
        ie = len(self.walk)
        while index < ie:
            try:
                segment = self.walk[index + 1]
            except IndexError:
                self.remove_biggest_loop_in_range(start, index)
                return
            if segment is None or segment.value == "RUNG":
                # Segment is essential.
                if start != index:
                    ie -= self.remove_biggest_loop_in_range(start, index)
                start = index + 2
            index += 2

    def remove_scaffold_ends_in_range(self, start, end):
        new_end = end
        limit = start + 2
        while new_end >= limit:
            j_segment = self.walk[new_end - 1]
            if j_segment is None or j_segment.value == "RUNG":
                if new_end == end:
                    break
                del self.walk[new_end + 1 : end + 1]
                end = new_end
                break
            new_end -= 2
        new_start = start
        limit = end - 2
        while new_start <= limit:
            j_segment = self.walk[new_start + 1]
            if j_segment is None or j_segment.value == "RUNG":
                if new_start == start:
                    break
                del self.walk[start:new_start]
                break
            new_start += 2

    def clip_scaffold_ends(self):
        """Finds contiguous regions, and calls removeScaffoldEnds on that range."""
        end = len(self.walk) - 1
        index = end
        while index >= 0:
            try:
                segment = self.walk[index - 1]
            except IndexError:
                self.remove_scaffold_ends_in_range(index, end)
                return
            if segment is None:
                self.remove_scaffold_ends_in_range(index, end)
                end = index - 2
            index -= 2

    def two_opt(self):
        """
        Unused
        """
        v = self.get_value()
        while True:
            new_value = self.two_opt_cycle(v)
            if v == new_value:
                break

    def two_opt_cycle(self, value):
        """
        Unused
        """
        if len(self.walk) == 0:
            return 0
        swap_start = 0
        walk_end = len(self.walk)
        while swap_start < walk_end:
            swap_element = self.walk[swap_start]
            m = swap_element.visited
            swap_end = swap_start + 2
            while swap_end < walk_end:
                current_element = self.walk[swap_end]
                if swap_element == current_element:
                    m -= 1
                    self.flip_start = swap_start + 1
                    self.flip_end = swap_end - 1
                    new_value = self.get_value()
                    if new_value > value:
                        value = new_value
                        self.walk[swap_start + 1 : swap_end] = self.walk[
                            swap_start + 1 : swap_end : -1
                        ]  # reverse
                    else:
                        self.flip_start = None
                        self.flip_end = None
                    if m == 0:
                        break
                swap_end += 2
            swap_start += 2
        return value

    def get_segment(self, index):
        """
        Unused
        """
        if (
            self.flip_start is not None
            and self.flip_end is not None
            and self.flip_start <= index <= self.flip_end
        ):
            return self.walk[self.flip_end - (index - self.flip_start)]
        return self.walk[index]

    def get_node(self, index):
        """
        Unused
        """
        if (
            self.flip_start is not None
            and self.flip_end is not None
            and self.flip_start <= index <= self.flip_end
        ):
            return self.walk[self.flip_end - (index - self.flip_start)]
        try:
            return self.walk[index]
        except IndexError:
            return None

    def get_value(self):
        """
        Path values with flip.
        @return: Flipped path value.
        """
        if len(self.walk) == 0:
            return 0
        value = 0
        start = 0
        end = len(self.walk) - 1
        while start < end:
            i_segment = self.get_segment(start + 1)
            if i_segment.value == "RUNG":
                break
            start += 2
        while end >= 2:
            i_segment = self.get_segment(end - 1)
            if i_segment.value == "RUNG":
                break
            end -= 2
        j = start
        while j < end:
            j_node = self.get_node(j)
            j += 1
            j_segment = self.get_segment(j)
            j += 1
            if j_segment.value != "RUNG":
                # if the node connector is not critical, try to find and skip a loop
                k = j
                while k < end:
                    k_node = self.get_node(k)
                    k += 1
                    k_segment = self.get_segment(k)
                    k += 1
                    if k_segment.value == "RUNG":
                        break
                    if k_node == j_node:
                        # Only skippable nodes existed before returned to original node, so skip that loop.
                        value += (k - j) * 10
                        j = k
                        j_segment = k_segment
                        break
            if j_segment.value == "SCAFFOLD":
                value -= j_segment.a.distance_sq(j_segment.b)
            elif j_segment.value == "RUNG":
                value -= j_segment.a.distance_sq(j_segment.b)
        return value


class VectorMontonizer:
    """
    Sorts all segments according to their highest y values. Steps through the values in order
    each step activates and deactivates the segments that are encountered such that it always has a list
    of active segments. Sorting the active segments according to their x-intercepts gives a list of all
    points that a ray would strike passing through that shape. Every other such area is filled. These are
    given rungs, and connected to intercept points.
    """

    def __init__(
        self, low_value=-float("inf"), high_value=float("inf"), start=-float("inf")
    ):
        self._event_index = 0
        self._events = []
        self._dirty_event_sort = True

        self._actives = []
        self._dirty_actives_sort = True

        self._dirty_scanline = True

        self.scanline = start
        self.valid_low = low_value
        self.valid_high = high_value

        self.scanbeam_low = float("inf")
        self.scanbeam_high = -float("inf")

    def add_segment_events(self, links):
        """
        Add segment to be processed. This segment should already exist and have the correct type
        @param links:
        @return:
        """
        self._dirty_scanline = True
        self._dirty_event_sort = True
        self._dirty_actives_sort = True
        for s in links:
            self._events.append((s[4].y, s))  # High
            self._events.append((s[5].y, s))  # Low

    def add_polyline(self, path):
        """
        Add segments in the form of a connected path. These positions are read and segments are created for these
        points.

        @param path:
        @return:
        """
        self._dirty_scanline = True
        self._dirty_event_sort = True
        self._dirty_actives_sort = True
        for i in range(len(path) - 1):
            p0 = path[i]
            p1 = path[i + 1]
            if p0.y > p1.y:
                high = p0
                low = p1
            else:
                high = p1
                low = p0

            # b = low.y - (m * low.x)
            if self.valid_low > high.y:
                # Cluster before range.
                continue
            if self.valid_high < low.y:
                # Cluster after range.
                continue
            seg = Segment(p0, p1)
            # cluster = [False, i, p0, p1, high, low, m, b, path]
            if self.valid_low < low.y:
                self._events.append((low.y, seg))
            if self.valid_high > high.y:
                self._events.append((high.y, seg))
            if high.y >= self.scanline >= low.y:
                seg.active = True
                self._actives.append(seg)

    def current_is_valid_range(self):
        return self.valid_high >= self.scanline >= self.valid_low

    def scanline_increment(self, delta):
        self.scanline_to(self.scanline + delta)
        self._sort_actives()
        return self.current_is_valid_range()

    def scanline_to(self, scan):
        """
        Move the scanline to the scan position.
        @param scan:
        @return:
        """
        self._dirty_actives_sort = True
        self._sort_events()
        self._find_scanbeam()

        while self._below_scanbeam(scan):
            c = self.scanbeam_higher()
            if c.active:
                c.active = False
                self._actives.remove(c)
            else:
                c.active = True
                self._actives.append(c)

        while self._above_scanbeam(scan):
            c = self.scanbeam_lower()
            if c.active:
                c.active = False
                self._actives.remove(c)
            else:
                c.active = True
                self._actives.append(c)

        self.scanline = scan

    def is_point_inside(self, x, y, tolerance=0):
        """
        Determine if the x/y point is with the segments of a closed shape polygon.

        This assumes that add_polyline added a closed point class.
        @param x: x location of point
        @param y: y location of point
        @param tolerance: wiggle room
        @return:
        """
        self.scanline_to(y)
        self._sort_actives()
        for i in range(1, len(self._actives), 2):
            prior = self._actives[i - 1]
            after = self._actives[i]
            if (
                self.intercept(prior, y) - tolerance
                <= x
                <= self.intercept(after, y) + tolerance
            ):
                return True
        return False

    def actives(self):
        """
        Get the active list at the current scanline.

        @return:
        """
        self._sort_actives()
        return self._actives

    def event_range(self):
        """
        Returns the range of events from the lowest to the highest in y-value.

        @return:
        """
        self._sort_events()
        y_min = self._events[0][0]
        y_max = self._events[-1][0]
        return y_min, y_max

    def _sort_events(self):
        if not self._dirty_event_sort:
            return
        self._events.sort(key=lambda e: e[0])
        self._dirty_event_sort = False

    def _sort_actives(self):
        if not self._dirty_actives_sort:
            return
        self._actives.sort(key=self.intercept)
        self._dirty_actives_sort = False

    def intercept(self, e, y=None):
        if y is None:
            y = self.scanline
        m = e[6]
        b = e[7]
        if m == float("nan") or m == float("inf"):
            low = e[5]
            return low.x
        return (y - b) / m

    def _find_scanbeam(self):
        if not self._dirty_scanline:
            return
        self._dirty_scanline = False
        self._sort_events()

        self._event_index = -1
        self.scanbeam_high = -float("inf")
        self.scanbeam_lower()

        while self._above_scanbeam(self.scanline):
            self.scanbeam_lower()

    def within_scanbeam(self, v):
        """
        Is the value within the current scanbeam?
        @param v:
        @return:
        """

        return not self._below_scanbeam(v) and not self._above_scanbeam(v)

    def _below_scanbeam(self, v):
        """
        Is the value below the current scanbeam?
        @param v:
        @return:
        """
        return v < self.scanbeam_low

    def _above_scanbeam(self, v):
        """
        Is the value above the current scanbeam?

        @param v:
        @return:
        """
        return v > self.scanbeam_high

    def scanbeam_lower(self):
        """
        Move the scanbeam lower through the events.

        @return:
        """
        self._event_index += 1
        self.scanbeam_low = self.scanbeam_high
        if self._event_index < len(self._events):
            self.scanbeam_high = self._events[self._event_index][0]
        else:
            self.scanbeam_high = float("inf")
        if self._event_index > 0:
            return self._events[self._event_index - 1][1]
        else:
            return None

    def scanbeam_higher(self):
        """
        Move the scanbeam higher in the events.

        @return:
        """
        self._event_index -= 1
        self.scanbeam_high = self.scanbeam_low
        if self._event_index > 0:
            self.scanbeam_low = self._events[self._event_index - 1][0]
        else:
            self.scanbeam_low = -float("inf")
        return self._events[self._event_index][1]


class EulerianFill:
    """Eulerian fill given some outline shapes, creates a fill."""

    def __init__(self, distance):
        self.distance = distance
        self.outlines = []

    def __iadd__(self, other):
        self.outlines.append(other)
        return self

    def estimate(self):
        min_y = float("inf")
        max_y = -float("inf")
        for outline in self.outlines:
            o_min_y = min([p[1] for p in outline])
            o_max_y = max([p[1] for p in outline])
            min_y = min(min_y, o_min_y)
            max_y = max(max_y, o_max_y)
        try:
            return (max_y - min_y) / self.distance
        except ZeroDivisionError:
            return float("inf")

    def get_fill(self):
        min_y = float("inf")
        max_y = -float("inf")
        outline_graphs = list()
        for outline in self.outlines:
            outline_graph = Graph()
            outline_graph.add_shape(outline, True)
            o_min_y = min([p[1] for p in outline])
            o_max_y = max([p[1] for p in outline])
            min_y = min(min_y, o_min_y)
            max_y = max(max_y, o_max_y)
            outline_graphs.append(outline_graph)
        graph = Graph()
        Graph.monotone_fill(graph, outline_graphs, min_y, max_y, self.distance)
        graph.double_odd_edge()
        walk = list()
        graph.walk(walk)
        return walk
