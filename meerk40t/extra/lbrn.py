"""
Parser for .lbrn Lightburn files.

Lightburn files are xml files denoting simple types with a narrowly nested style. They come in two main flavors,
.lbrn and .lbrn2 files, the latter of which has a bit of optimization for loading efficiency.

"""
import base64
import re
from io import BytesIO
from xml.etree.ElementTree import ParseError, iterparse

import PIL.Image

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.units import UNITS_PER_MM
from meerk40t.svgelements import Color, Matrix
from meerk40t.tools.geomstr import Geomstr


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("load/LbrnLoader", LbrnLoader)


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


class LbrnLoader:
    @staticmethod
    def load_types():
        yield "LightBurn Files", ("lbrn", "lbrn2"), "application/x-lbrn"

    @staticmethod
    def parse(pathname, source, elements):
        op_branch = elements.op_branch
        elem_branch = elements.elem_branch

        op_branch.remove_all_children()
        elem_branch.remove_all_children()
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
        for event, elem in iterparse(source, events=("start", "end")):
            if event == "start":
                siblings = children
                parent = (parent, children)
                children = list()
                node = (elem, children)
                siblings.append(node)
                if elem.tag == "LightBurnProject":
                    app_version = elem.attrib.get("AppVersion")
                    _format = elem.attrib.get("FormatVersion")
                    material_height = elem.attrib.get("MaterialHeight")
                    try:
                        cx = elements.space.width / 2
                        cy = elements.space.height / 2
                    except AttributeError:
                        cx = 0
                        cy = 0
                    mirror_x = elem.attrib.get("MirrorX")
                    mirror_y = elem.attrib.get("MirrorY")
                    if mirror_x == "True":
                        matrix.post_scale_x(-1, cx, cy)
                    if mirror_y == "True":
                        matrix.post_scale_y(-1, cx, cy)

                elif elem.tag in ("Shape", "BackupPath"):
                    stack.append((context, matrix))
                    matrix = Matrix(matrix)
                    _type = elem.attrib.get("Type")
                    if _type == "Group":
                        context = context.add(type="group")
                    elif _type in "Text":
                        context = context.add(
                            type="group", label=elem.attrib.get("Str")
                        )
                elif elem.tag == "Thumbnail":
                    pass
                    # thumb_source_data = base64.b64decode(elem.attrib.get("Source"))
                    # stream = BytesIO(thumb_source_data)
                    # image = PIL.Image.open(stream)
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
                elif elem.tag == "CutSetting_Img":
                    values = {"tag": elem.tag}
                    for c, c_children in children:
                        values[c.tag] = c.attrib.get("Value")
                    values.update(elem.attrib)

                    op_type = values.get("type")
                    cut_settings_img[values["index"]] = values
                    if op_type == "Image":
                        values["op"] = values["op"] = op_branch.add(
                            type="op image",
                            label=values.get("name"),
                            speed=float(values.get("speed", DEFAULT_SPEED)),
                            power=float(values.get("maxPower", DEFAULT_POWER)) * 10.0,
                        )
                elif elem.tag == "CutSetting":
                    values = {"tag": elem.tag}
                    for c, c_children in children:
                        values[c.tag] = c.attrib.get("Value")
                    values.update(elem.attrib)

                    op_type = values.get("type")
                    cut_settings[values["index"]] = values
                    if op_type == "Cut":
                        values["op"] = op_branch.add(
                            type="op cut",
                            label=values.get("name"),
                            speed=float(values.get("speed", DEFAULT_SPEED)),
                            power=float(values.get("maxPower", DEFAULT_POWER)) * 10.0,
                        )
                    elif op_type == "Scan":
                        values["op"] = op_branch.add(
                            type="op raster",
                            label=values.get("name"),
                            speed=float(values.get("speed", DEFAULT_SPEED)),
                            power=float(values.get("maxPower", DEFAULT_POWER)) * 10.0,
                        )
                    else:
                        values["op"] = op_branch.add(
                            type="op engrave",
                            label=values.get("name"),
                            speed=float(values.get("speed", DEFAULT_SPEED)),
                            power=float(values.get("maxPower", DEFAULT_POWER)) * 10.0,
                        )
                elif elem.tag == "XForm":
                    matrix = Matrix(*map(float, elem.text.split(" "))) * matrix
                elif elem.tag in ("Shape", "BackupPath"):
                    _type = elem.attrib.get("Type")
                    if primlist is None:
                        primlist = "".join(prims)
                        prims.clear()
                    if vertlist is None:
                        vertlist = "".join(verts)
                        verts.clear()
                    values = {"tag": elem.tag, "type": _type}
                    values.update(elem.attrib)
                    color = Color("black")
                    _cut_index = elem.attrib.get("CutIndex")
                    _cut_settings = cut_settings.get(_cut_index, None)
                    if _type == "Text":
                        if not bool(int(values.get("HasBackupPath", 0))):
                            text = values.get("Str")
                            node = context.add(
                                type="elem text",
                                label=text,
                                text=text,
                                matrix=matrix,
                                font=values.get("Font"),
                                stroke=color,
                            )
                            _cut_settings.get("op").add_reference(node)
                    elif _type == "Path":
                        geometry = geomstr_from_vert_list(vertlist, primlist)
                        geometry.transform(matrix)
                        node = context.add(
                            type="elem path", geometry=geometry, stroke=color
                        )
                        _cut_settings.get("op").add_reference(node)
                    elif _type == "Rect":
                        width = float(values.get("W", 0))
                        height = float(values.get("H", 0))
                        node = context.add(
                            type="elem rect",
                            x=-width / 2,
                            y=-height / 2,
                            width=width,
                            height=height,
                            stroke=color,
                            matrix=matrix,
                        )
                        _cut_settings.get("op").add_reference(node)
                    elif _type == "Ellipse":
                        node = context.add(
                            type="elem ellipse",
                            cx=0,
                            cy=0,
                            rx=float(values.get("Rx", 0)),
                            ry=float(values.get("Ry", 0)),
                            stroke=color,
                            matrix=matrix,
                        )
                        _cut_settings.get("op").add_reference(node)
                    elif _type == "Polygon":
                        rx = float(values.get("Rx", 0))
                        ry = float(values.get("Ry", 0))
                        geometry = Geomstr.regular_polygon(
                            number_of_vertex=int(values.get("N")),
                            radius=1.0,
                            radius_inner=1.0,
                        )
                        matrix.pre_scale(rx, ry)
                        geometry.transform(matrix)
                        node = context.add(
                            type="elem path", geometry=geometry, stroke=color
                        )
                        _cut_settings.get("op").add_reference(node)
                    elif _type == "Bitmap":
                        # Needs image specific settings.
                        _cut_settings = cut_settings_img.get(_cut_index, None)

                        data = elem.attrib.get("Data")
                        if data is None:
                            continue
                        thumb_source_data = base64.b64decode(data)
                        stream = BytesIO(thumb_source_data)
                        image = PIL.Image.open(stream)
                        width = float(values.get("W"))
                        height = float(values.get("H"))
                        matrix.pre_translate(-width / 2, -height / 2)
                        matrix.pre_scale(width / image.width, height / image.height)
                        node = context.add(
                            type="elem image",
                            image=image,
                            matrix=matrix,
                        )
                        _cut_settings.get("op").add_reference(node)
                    vertlist = None
                    primlist = None
                    context, matrix = stack.pop()
                elif elem.tag == "V":
                    # FormatVersion 0
                    verts.append(
                        f"V{elem.attrib.get('vx', 0)} {elem.attrib.get('vy', 0)}"
                    )
                    c0x = elem.attrib.get("c0x")
                    c0y = elem.attrib.get("c0y")
                    c1x = elem.attrib.get("c1x")
                    c1y = elem.attrib.get("c1y")
                    if c0x and c0y:
                        verts.append(f"c0x{c0x}c0y{c0y}")
                    else:
                        verts.append("c0x1")
                    if c1x and c1y:
                        verts.append(f"c1x{c1x}c1y{c1y}")
                    else:
                        verts.append("c1x1")
                elif elem.tag == "P":
                    # FormatVersion 0
                    prims.append(
                        f"{elem.attrib.get('T')}{elem.attrib.get('p0', 0)} {elem.attrib.get('p1', 0)}"
                    )
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

        context.focus()

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        try:
            with open(pathname, "r") as source:
                try:
                    LbrnLoader.parse(pathname, source, elements_service)
                except ParseError:
                    # This is likely `Junk after Document` which is already parsed. Unsure if this is because the
                    # format will sometimes have some extra information or because of a malformed xml.
                    pass
        except (IOError, IndexError) as e:
            raise BadFileError(str(e)) from e
        elements_service._loading_cleared = True
        return True
