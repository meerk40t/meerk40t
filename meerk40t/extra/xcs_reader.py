"""
Parser for .xcs XTool

XTool Creative Space

"""
import json
import base64
import re
from io import BytesIO

import PIL.Image

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Color, Matrix
from meerk40t.tools.geomstr import Geomstr

from pprint import pprint

def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("load/XCSLoader", XCSLoader)


DEFAULT_SPEED = 30
DEFAULT_POWER = 30


_prim_parse = [
    ("CONNECT", r"([0-9]+ [0-9]+)"),
    ("TYPE", r"(B|L)"),
    ("SKIP", r"[ ,\t\n\x09\x0A\x0C\x0D]+"),
]
prim_re = re.compile("|".join("(?P<%s>%s)" % pair for pair in _prim_parse))

_vert_parse = [
    (
        "POINT",
        r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)? [-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)",
    ),
    ("SKIP", r"[ ,\t\n\x09\x0A\x0C\x0D]+"),
    ("VERTEX", r"(V)"),
    ("SFLAG", r"(S)"),
    ("CONTROL", r"(c0x|c0y|c1x|c1y)"),
    ("NUM", r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"),
]
vert_re = re.compile("|".join("(?P<%s>%s)" % pair for pair in _vert_parse))


def vert_parser(text: str):
    p = 0
    limit = len(text)
    while p < limit:
        match = vert_re.match(text, p)
        if match is None:
            break  # No more matches.
        _kind = match.lastgroup
        _start = p
        p = match.end()
        if _kind == "SKIP":
            continue
        _value = match.group()
        yield _kind, _value, _start, p


def prim_parser(text: str):
    p = 0
    limit = len(text)
    while p < limit:
        match = prim_re.match(text, p)
        if match is None:
            break  # No more matches.
        _kind = match.lastgroup
        _start = p
        p = match.end()
        if _kind == "SKIP":
            continue
        _value = match.group()
        yield _kind, _value, _start, p


def geomstr_from_vert_list(vertlist, plist):
    geomstr = Geomstr()

    vmap = None
    data_type = None

    vert_lookup = list()

    def vert_commit():
        if vmap:
            if "c0y" in vmap:
                vmap["c0"] = complex(vmap.get("c0x", 0), vmap.get("c0y", 0))
            if "c1y" in vmap:
                vmap["c1"] = complex(vmap.get("c1x", 0), vmap.get("c1y", 0))
            vert_lookup.append(vmap)

    for kind, value, start, pos in vert_parser(vertlist):
        if kind == "VERTEX":
            vert_commit()
            vmap = {}
            data_type = "V"
        elif kind == "SFLAG":
            vmap[value] = True
        elif kind == "POINT":
            vmap[data_type] = complex(*list(map(float, value.split(" "))))
        elif kind == "NUM":
            vmap[data_type] = float(value)
        elif kind == "CONTROL":
            data_type = value
    vert_commit()

    if plist == "LineClosed":
        size = len(vert_lookup)
        for i in range(size + 1):
            v0 = vert_lookup[i % size]
            v1 = vert_lookup[(i + 1) % size]
            start = v0.get("V")
            end = v1.get("V")
            geomstr.line(start, end)
        return geomstr
    elif plist == "":
        size = len(vert_lookup)
        if size == 0:
            return geomstr
        for i in range(size + 1):
            v0 = vert_lookup[i % size]
            v1 = vert_lookup[(i + 1) % size]
            start = v0.get("V")
            end = v1.get("V")
            c0 = v0.get("c0")
            c1 = v1.get("c1")
            if c0 and c1:
                geomstr.cubic(start, c0, c1, end)
            else:
                geomstr.line(start, end)
        return geomstr
    for kind, value, start, pos in prim_parser(plist):
        if kind == "TYPE":
            data_type = value
        elif kind == "CONNECT":
            indexes = list(map(int, value.split(" ")))
            try:
                v0 = vert_lookup[indexes[0]]
                v1 = vert_lookup[indexes[1]]
            except IndexError:
                continue
            start = v0.get("V")
            end = v1.get("V")
            if data_type == "L":
                geomstr.line(start, end)
            else:
                c0 = v0.get("c0")
                c1 = v1.get("c1")
                geomstr.cubic(start, c0, c1, end)
    return geomstr

def parse_line(elements, context, content):
    print ("PARSING LINE")
    pprint (content)
    return context

def parse_rect(elements, context, content):
    print ("PARSING RECT")
    pprint (content)
    return context

class XCSLoader:
    @staticmethod
    def load_types():
        yield "XTool Files", ("xcs", ), "application/x-xcs"

    @staticmethod
    def parse(pathname, source, elements):
        print ("Parsing started....")
        op_branch = elements.op_branch
        elem_branch = elements.elem_branch

        # op_branch.remove_all_children()
        # elem_branch.remove_all_children()
        context = elem_branch.add(type="file", filepath=pathname)

        vertlist = None
        primlist = None
        verts = []
        prims = []

        matrix = Matrix.scale(UNITS_PER_MM)
        stack = []
        parent = None  # Root Node
        children = list()
        cut_settings = dict()
        cut_settings_img = dict()
        try:
            xcs_data = json.load(source)
        except Exception as e:
            raise BadFileError(str(e)) from e
        if not "canvas" in xcs_data:
            raise BadFileError("No canvas found")

        for canvas in xcs_data["canvas"]:
            if not "displays" in canvas:
                continue
            displays = canvas["displays"]
            for disp in displays:
                mode = disp.get("type", "")
                if mode == "LINE":
                    context = parse_line(elements=elements, context=context, content=disp)
                elif mode == "RECT":
                    context = parse_rect(elements=elements, context=context, content=disp)
                else:
                    print (f"Unknown type: {mode}")
                    pprint (disp)
                # pprint (disp)
        print ("Parsing ended")
        context.focus()

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        try:
            with open(pathname, "r") as source:
                XCSLoader.parse(pathname, source, elements_service)
        except (IOError, IndexError) as e:
            raise BadFileError(str(e)) from e
        elements_service._loading_cleared = True
        return True

