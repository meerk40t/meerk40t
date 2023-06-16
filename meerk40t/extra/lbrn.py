"""
Parser for .lbrn Lightburn files.

Lightburn files are xml files denoting simple types with a narrowly nested style. They come in two main flavors,
.lbrn and .lbrn2 files, the latter of which has a bit of optimization for loading efficiency.

"""
import base64
import re
from io import BytesIO
from xml.etree.ElementTree import iterparse

import PIL.Image
from meerk40t.core.units import UNITS_PER_MM

from meerk40t.tools.geomstr import Geomstr

from meerk40t.core.exceptions import BadFileError
from meerk40t.svgelements import Matrix, Color


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("load/LbrnLoader", LbrnLoader)


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


def geomstry_from_vert_list(vertlist, plist):
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
        elif kind == "POINT":
            vmap[data_type] = complex(*list(map(float, value.split(" "))))
        elif kind == "NUM":
            vmap[data_type] = float(value)
        elif kind == "CONTROL":
            data_type = value
    vert_commit()

    for kind, value, start, pos in prim_parser(plist):
        if kind == "TYPE":
            data_type = value
        elif kind == "CONNECT":
            indexes = list(map(int, value.split(" ")))
            try:
                v0 = vert_lookup[indexes[0]]
                v1 = vert_lookup[indexes[1]]
            except IndexError:
                print("WTF")
                continue
            start = v0.get("V")
            end = v1.get("V")
            if data_type == "L":
                geomstr.line(start, end)
            else:
                c0 = v0.get("c0")
                c1 = v1.get("c1")
                if c0 and c1:
                    geomstr.cubic(start, c0, c1, end)
                else:
                    print("This is also wrong.")
    return geomstr


class LbrnLoader:
    @staticmethod
    def load_types():
        yield "LightBurn Files", ("lbrn", "lbrn2"), "application/x-lbrn"

    @staticmethod
    def parse(pathname, source, elements):
        regmark = elements.reg_branch
        op_branch = elements.op_branch
        elem_branch = elements.elem_branch

        width = elements.device.unit_width
        height = elements.device.unit_height

        op_branch.remove_all_children()
        elem_branch.remove_all_children()
        file_node = elem_branch.add(type="file", filepath=pathname)
        matrix = None
        vertlist = None
        primlist = None

        parent = None  # Root Node
        children = list()
        cut_settings = dict()
        for event, elem in iterparse(source, events=("start", "end")):
            if event == "start":
                siblings = children
                parent = (parent, children)
                children = list()
                node = (elem, children)
                siblings.append(node)
                if elem.tag == "LightBurnProject":
                    app_version = elem.attrib.get("AppVersion")
                    format = elem.attrib.get("FormatVersion")
                    material_height = elem.attrib.get("MaterialHeight")
                    mirror_x = elem.attrib.get("MirrorX")
                    mirror_y = elem.attrib.get("MirrorY")

                elif elem.tag == "Thumbnail":
                    thumb_source_data = base64.b64decode(elem.attrib.get("Source"))
                    stream = BytesIO(thumb_source_data)
                    image = PIL.Image.open(stream)

            elif event == "end":
                if elem.tag == "VariableText":
                    values = {"tag": elem.tag}
                    for c, c_children in children:
                        values[c.tag] = c.attrib.get("Value")
                    values.update(elem.attrib)

                elif elem.tag == "UIPrefs":
                    values = {"tag": elem.tag}
                    for c, c_children in children:
                        values[c.tag] = c.attrib.get("Value")
                    values.update(elem.attrib)

                elif elem.tag == "CutSetting":
                    values = {"tag": elem.tag, "type": elem.attrib.get("Type")}
                    for c, c_children in children:
                        values[c.tag] = c.attrib.get("Value")
                    values.update(elem.attrib)
                    cut_settings[values["index"]] = values

                elif elem.tag == "XForm":
                    matrix = Matrix(*map(float, elem.text.split(" ")))
                    matrix.post_scale(UNITS_PER_MM)
                elif elem.tag == "Shape":
                    _type = elem.attrib.get("Type")
                    values = {"tag": elem.tag, "type": _type}
                    values.update(elem.attrib)
                    _cut_index = elem.attrib.get("CutIndex")
                    _cut_settings = cut_settings.get(_cut_index)
                    color = Color("black")
                    if _type == "Text":
                        geometry = geomstry_from_vert_list(vertlist, primlist)
                        geometry.transform(matrix)
                        file_node.add(type="elem path", geometry=geometry, stroke=color)
                    elif _type == "Path":
                        geometry = geomstry_from_vert_list(vertlist, primlist)
                        geometry.transform(matrix)
                        file_node.add(type="elem path", geometry=geometry, stroke=color)
                    elif _type == "Rect":
                        file_node.add(
                            type="elem rect",
                            x=0,
                            y=0,
                            width=float(values.get("W", 0)),
                            height=float(values.get("H", 0)),
                            stroke=color,
                            matrix=matrix
                        )
                    elif _type == "Ellipse":
                        file_node.add(
                            type="elem ellipse",
                            cx=0,
                            cy=0,
                            rx=float(values.get("Rx", 0)),
                            ry=float(values.get("Ry", 0)),
                            stroke=color,
                            matrix=matrix
                        )
                    elif _type == "Polygon":
                        geometry = Geomstr.regular_polygon(
                            number_of_vertex=int(values.get("N")),
                            radius=float(values.get("Ry", 0)),
                            radius_inner=float(values.get("Rx", 0)),
                        )
                        geometry.transform(matrix)
                        # geometry.uscale(UNITS_PER_MM)
                        file_node.add(type="elem path", geometry=geometry, stroke=color)
                elif elem.tag == "VertList":
                    vertlist = elem.text
                elif elem.tag == "PrimList":
                    primlist = elem.text
                elif elem.tag == "Notes":
                    values = {"tag": elem.tag}
                    values.update(elem.attrib)
                    note = values.get("Notes")
                    if note:
                        elements.note = note

                parent, children = parent

        file_node.focus()

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        try:
            with open(pathname, "r") as source:
                LbrnLoader.parse(pathname, source, elements_service)
        except (IOError, IndexError) as e:
            raise BadFileError(str(e)) from e
        return True
