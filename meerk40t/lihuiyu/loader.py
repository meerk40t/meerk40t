from meerk40t.core.cutcode import CutCode, RawCut
from meerk40t.lihuiyu.parser import LihuiyuParser


class EGVBlob:
    def __init__(self, data: bytearray, name=None):
        self.name = name
        self.data = data
        self.operation = "blob"
        self._cutcode = None
        self._cut = None

    def __repr__(self):
        return f"EGV({self.name}, {len(self.data)} bytes)"

    def as_cutobjects(self):
        parser = LihuiyuParser()
        self._cutcode = CutCode()
        self._cut = RawCut()

        def new_cut():
            if self._cut is not None and len(self._cut):
                self._cutcode.append(self._cut)
            self._cut = RawCut()
            self._cut.settings = dict(parser.settings)

        def position(p):
            if p is None or self._cut is None:
                new_cut()
                return

            from_x, from_y, to_x, to_y = p

            if parser.program_mode:
                if len(self._cut.plot) == 0:
                    self._cut.plot_append(int(from_x), int(from_y), parser.laser)
                self._cut.plot_append(int(to_x), int(to_y), parser.laser)
            else:
                new_cut()

        parser.position = position
        parser.header_write(self.data)

        cutcode = self._cutcode
        self._cut = None
        self._cutcode = None
        return cutcode

    def generate(self):
        yield "blob", "egv", LihuiyuParser.remove_header(self.data)


class EgvLoader:
    @staticmethod
    def remove_header(data):
        count_lines = 0
        count_flag = 0
        for i in range(len(data)):
            b = data[i]
            c = chr(b)
            if c == "\n":
                count_lines += 1
            elif c == "%":
                count_flag += 1
            if count_lines >= 3 and count_flag >= 5:
                return data[i:]

    @staticmethod
    def load_types():
        yield "Engrave Files", ("egv",), "application/x-egv"

    @staticmethod
    def load(kernel, elements_modifier, pathname, **kwargs):
        import os

        basename = os.path.basename(pathname)
        with open(pathname, "rb") as f:
            op_branch = elements_modifier.get(type="branch ops")
            op_branch.add(
                data=bytearray(EgvLoader.remove_header(f.read())),
                data_type="egv",
                type="blob",
                name=basename,
            )
        return True
