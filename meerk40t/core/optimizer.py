from meerk40t.svgelements import Point


class Optimizer:
    def __init__(self, cutcode):
        self.cutcode = cutcode

    def optimize(self):
        old_len = self.length_travel()
        self.optimize_travel()
        new_len = self.length_travel()
        red = new_len-old_len
        try:
            print("%f -> %f reduced %f (%f%%)" % (old_len, new_len, red, 100 * (red/old_len)))
        except ZeroDivisionError:
            pass

    def length_travel(self):
        subpaths = self.cutcode
        distance = 0.0
        for i in range(1, len(subpaths)):
            prev = subpaths[i-1]
            curr = subpaths[i]
            distance += Point.distance(prev.end(), curr.start())
        return distance

    def delta_distance(self, j, k):
        subpaths = self.cutcode
        distance = 0.0
        k -= 1
        a1 = subpaths[j].start()
        b0 = subpaths[k].end()
        if k < len(subpaths) - 1:
            b1 = subpaths[k + 1].start()
            d = Point.distance(b0, b1)
            distance -= d
            d = Point.distance(a1, b1)
            distance += d
        if j > 0:
            a0 = subpaths[j - 1].end()
            d = Point.distance(a0, a1)
            distance -= d
            d = Point.distance(a0, b0)
            distance += d
        return distance

    def cross(self, j, k):
        """
        Reverses subpaths flipping the individual elements from position j inclusive to
        k exclusive.
        :param subpaths:
        :param j:
        :param k:
        :return:
        """
        subpaths = self.cutcode
        for q in range(j, k):
            subpaths[q].reverse()
        subpaths[j:k] = subpaths[j:k][::-1]

    def optimize_travel(self):
        cutcode = self.cutcode
        improved = True
        while improved:
            improved = False
            for j in range(len(cutcode)):
                for k in range(j + 1, len(cutcode)):
                    new_cut = self.delta_distance(j, k)
                    if new_cut < 0:
                        self.cross(j, k)
                        improved = True
