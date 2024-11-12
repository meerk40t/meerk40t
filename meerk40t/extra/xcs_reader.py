"""
Parser for .xcs XTool Creative Space files
The format is mostly a json file that holds a couple of relevant sections
"canvasId"          "95eac905-c7b1-4619-8e71-82ff4471dc89" uuid of canvas
"extid"             external id (?)
"device"            holds device information, see section device
"version"           "2.2.23" version of xcs that created this file
"created"           timestamp for creation
"modified"          timestamp for modification
"ua"                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) xToolCreativeSpace/2.2.23 Chrome/116.0.5845.228 Electron/26.6.3 Safari/537.36" possible readers
"meta"              Metadata (?)
"cover"             embedded preview image
"minRequiredVersion"    --
"canvas             main information holder, see section canvas

Section device
--------------
"id"                ""
"power"             "0"
"data"
    "dataType"      "Map"
    "value"         []
"materialList"      []
"materialTypeList"  []

Section canvas
--------------

"""
import json
import base64
from io import BytesIO
from math import tau

import PIL.Image

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.units import UNITS_PER_MM, UNITS_PER_INCH, Length
from meerk40t.svgelements import Color, Matrix
from meerk40t.tools.geomstr import Geomstr

from pprint import pprint

def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("load/XCSLoader", XCSLoader)


DEFAULT_SPEED = 30
DEFAULT_POWER = 30


class XCSLoader:

    def __init__(self, context=None, elements=None, *args, **kwargs):
        self.channel = context.kernel.channels["console"]
        self.context = context
        self.elements = elements
        self.groups = {}

    @staticmethod
    def load_types():
        yield "XTool Files", ("xcs", ), "application/x-xcs"


    def fill_groups(self, canvas):
        self.groups = {}
        if "groupData" in canvas:
            groupdata = canvas["groupData"]
            # pprint (groupdata)
            for key, grp in groupdata.items():
                grp_id = grp.get("groupTag")
                label = grp.get("groupName", None)
                if grp_id:
                    self.groups[grp_id] = [label, None]  # label and associated node


    def get_matrix(self, content, use_scale: bool = True, use_rotate : bool = True, use_translate: bool = True):
        tx = 0
        ty = 0
        o_x = content.get("offsetX", 0)
        o_y = content.get("offsetY", 0)
        if use_rotate:
            # XCS does center around the center of the object
            # width and height are provided as the unrotated dimensions
            wd = content.get("width", 0)
            ht = content.get("height", 0)
            angle = content.get("angle", 0)
            angle = angle / 360 * tau
            px, py = self.get_coords(content, "pivot")
            px += wd / 2
            py += ht / 2
        else:
            angle = 0
            px = 0
            py = 0
        if use_scale:
            info = content.get("scale", None)
            if info:
                sx = round(info.get("x", 1), 8)
                if sx == 0:
                    sx = 1
                sy = round(info.get("y", 1), 8)
                if sy == 0:
                    sy = 1
        else:
            sx = 1
            sy = 1
        if use_translate:
            tx = self.to_length(content.get("offsetX", 0))
            ty = self.to_length(content.get("offsetY", 0))
        else:
            tx = 0
            ty = 0


        matrix = Matrix()
        if angle != 0:
            matrix.post_rotate(angle, px, py)
        if sx != 1 or sy != 1:
            matrix.post_scale(sx, sy)
        if tx != 0 or ty != 0:
            matrix.post_translate(tx, ty)

        return matrix

    @staticmethod
    def to_length(value):
        return round(value, 8) * UNITS_PER_MM


    def fix_position(self, node, content):
        x, y = self.get_coords(content)
        bb = node.bounds
        dx = x - bb[0]
        dy = y - bb[1]
        if abs(dx) > 50 or abs(dy) > 50:
            node.matrix *= Matrix.translate(dx, dy)
            node.translated(dx, dy)


    def get_coords(self, content, key=None):
        if key:
            x_coord = self.to_length(content[key].get("x", 0))
            y_coord = self.to_length(content[key].get("y", 0))
        else:
            x_coord = self.to_length(content.get("x", 0))
            y_coord = self.to_length(content.get("y", 0))
        return x_coord, y_coord

    def parse_line(self, parent, content):
        matrix = self.get_matrix(content, use_translate=False, use_scale=False, use_rotate=True)
        x_start, y_start = self.get_coords(content)
        x_offset = self.to_length(content.get("offsetX", 0))
        y_offset = self.to_length(content.get("offsetY", 0))
        x_end, y_end = self.get_coords(content, "endPoint")
        x_end += x_offset
        y_end += y_offset
        in_group, group_node = self.need_group(content, parent)
        ident = content.get("id", None)
        label = content.get("name", None)
        if label == "null":
            label = None
        set_hidden = not content.get("visible", True)
        stroke = Color(content.get("layerColor", "blue"))
        lock = content.get("lockState", False)
        p_node = group_node if in_group else parent
        node = p_node.add(
            type="elem line",
            label=label,
            x1=x_start,
            y1=y_start,
            x2=x_end,
            y2=y_end,
            id=ident,
            lock=lock,
            hidden=set_hidden,
            matrix=matrix,
            stroke=stroke,
        )
        self.fix_position(node, content)
        return parent

    def parse_rect(self, parent, content):
        matrix = self.get_matrix(content, use_scale=False, use_translate=False)
        x_start, y_start = self.get_coords(content)
        width = self.to_length(content.get("width", 0))
        height = self.to_length(content.get("height", 0))
        in_group, group_node = self.need_group(content, parent)
        ident = content.get("id", None)
        label = content.get("name", None)
        if label == "null":
            label = None
        set_hidden = not content.get("visible", True)
        stroke = Color(content.get("layerColor", "blue"))
        lock = content.get("lockState", False)
        p_node = group_node if in_group else parent
        # print (f"(xcs   ) x={Length(x_start).length_mm}, y={Length(y_start).length_mm}, width={Length(width).length_mm}, height={Length(height).length_mm}")
        # print (matrix)
        node = p_node.add(
            type="elem rect",
            label=label,
            x=x_start,
            y=y_start,
            width=width,
            height=height,
            id=ident,
            lock=lock,
            hidden=set_hidden,
            matrix=matrix,
            stroke=stroke,
        )
        bb = node.bounds
        # print (f"(bounds) x={Length(bb[0]).length_mm}, y={Length(bb[0]).length_mm}, width={Length(bb[2] - bb[0]).length_mm}, height={Length(bb[3] - bb[1]).length_mm}")
        return parent

    def parse_text(self, parent, content):
        matrix = self.get_matrix(content, use_translate=True)
        x_start, y_start = self.get_coords(content)
        width = self.to_length(content.get("width", 0))
        height = self.to_length(content.get("height", 0))
        in_group, group_node = self.need_group(content, parent)
        ident = content.get("id", None)
        label = content.get("name", None)
        if label == "null":
            label = None
        text_content = content.get("text", "")
        font_style = content.get("style", {})
        font_name = "Arial"
        font_size = Length("12pt")
        if "fontSize" in font_style:
            font_size = Length(f"{font_style['fontSize']}pt")
        if "fontName" in font_style:
            font_name = font_style['fontName']
        letter_spacing = font_style.get("letterSpacing", 0)
        alignment = font_style.get("align", "left")
        replacements = {
            "left": "start",
            "center": "middle",
            "right": "end",
        }
        if alignment in replacements:
            alignment = replacements[alignment]

        set_hidden = not content.get("visible", True)
        stroke = Color(content.get("layerColor", "blue"))
        lock = content.get("lockState", False)
        geom = Geomstr()
        if "charJSONs" in content:
            glyph_data = content["charJSONs"]
            for glyph in glyph_data:
                dx = glyph["x"]
                dy = glyph["y"]
                pathstr = glyph["dPath"]
                if not pathstr:
                    continue
                glyph_geom = Geomstr.svg(pathstr)
                glyph_geom.translate(dx, dy)
                geom.append(glyph_geom, end=True)
        else:
            font_data = content.get("fontData", None)
            if font_data:
                glyph_data = font_data.get("glyphData", {})
                dx = 0
                dy = 0
                for glyph in text_content:
                    if glyph not in glyph_data:
                        continue
                    info = glyph_data[glyph]
                    pathstr = info.get("dPath")
                    advance_x = info.get("advanceWidth", 0)
                    advance_y = info.get("advanceHeight", 0)
                    dx += advance_x + letter_spacing
                    if glyph == "\n":
                        dy += advance_y
                        dx = 0
                        continue
                    if not pathstr:
                        continue
                    glyph_geom = Geomstr.svg(pathstr)
                    glyph_geom.translate(dx, dy)
                geom.append(glyph_geom, end=True)
        geom.uscale(UNITS_PER_MM)
            # geom.translate(x_start, y_start)
        # Nothing found....
        if geom.index == 0:
            return
        p_node = group_node if in_group else parent
        node = p_node.add(
            type="elem path",
            label=label,
            id=ident,
            lock=lock,
            hidden=set_hidden,
            matrix=matrix,
            stroke=stroke,
            geometry=geom,
        )
        node.mktext = text_content
        node.mkfont = font_name
        node.mkfontsize = font_size
        node.mkalign = alignment
        # self.fix_position(node, content)
        return parent

    def parse_path(self, parent, content):
        matrix = self.get_matrix(content, use_translate=True)
        x_start, y_start = self.get_coords(content)
        width = self.to_length(content.get("width", 0))
        height = self.to_length(content.get("height", 0))
        in_group, group_node = self.need_group(content, parent)
        pathstr = content.get("dPath", None)
        if not pathstr:
            if self.channel:
                self.channel("Invalid path information")
            return
        geom = Geomstr.svg(pathstr)
        geom.uscale(UNITS_PER_MM)
        geom.translate(x_start, y_start)
        ident = content.get("id", None)
        label = content.get("name", None)
        if label == "null":
            label = None
        set_hidden = not content.get("visible", True)
        stroke = Color(content.get("layerColor", "blue"))
        lock = content.get("lockState", False)
        p_node = group_node if in_group else parent
        node = p_node.add(
            type="elem path",
            label=label,
            id=ident,
            lock=lock,
            hidden=set_hidden,
            matrix=matrix,
            stroke=stroke,
            geometry=geom,
        )
        self.fix_position(node, content)
        return parent

    def parse_circle(self, parent, content):
        matrix = self.get_matrix(content, use_translate=False, use_scale=False)
        x_start, y_start = self.get_coords(content)
        width = self.to_length(content.get("width", 0))
        height = self.to_length(content.get("height", 0))
        cx = x_start + width / 2
        cy = y_start + width / 2
        in_group, group_node = self.need_group(content, parent)
        ident = content.get("id", None)
        label = content.get("name", None)
        if label == "null":
            label = None
        set_hidden = not content.get("visible", True)
        stroke = Color(content.get("layerColor", "blue"))
        lock = content.get("lockState", False)
        p_node = group_node if in_group else parent
        node = p_node.add(
            type="elem ellipse",
            label=label,
            cx=cx,
            cy=cy,
            rx=width / 2,
            ry=height / 2,
            id=ident,
            lock=lock,
            hidden=set_hidden,
            matrix=matrix,
            stroke=stroke,
        )
        return parent

    def parse_bitmap(self, parent, content):
        if "base64" not in content:
            if self.channel:
                self.channel("Unknown content for bitmap")
            return
        rawdata = content["base64"]
        prefix = "data:image/png;base64,"
        if rawdata.startswith(prefix):
            rawdata = rawdata[len(prefix):]
        data = base64.b64decode(rawdata)
        stream = BytesIO(data)
        image = PIL.Image.open(stream)
        matrix = self.get_matrix(content, False)
        x_start, y_start = self.get_coords(content)
        width = self.to_length(content.get("width", 0))
        height = self.to_length(content.get("height", 0))
        # We need to prescale the image first...
        imagematrix = Matrix()
        imagematrix.pre_scale(width / image.width, height / image.height)
        matrix = imagematrix * matrix
        in_group, group_node = self.need_group(content, parent)
        ident = content.get("id", None)
        label = content.get("name", None)
        if label == "null":
            label = None
        set_hidden = not content.get("visible", True)
        stroke = Color(content.get("layerColor", "blue"))
        lock = content.get("lockState", False)
        p_node = group_node if in_group else parent
        node = p_node.add(
            type="elem image",
            label=label,
            id=ident,
            image=image,
            matrix=matrix,
            hidden=set_hidden,
            lock=lock,
        )
        return parent

    def parse_unknown(self, parent, content):
        if self.channel:
            self.channel(f"Unknown type {content.get('type', '??')}")
        pprint (content)
        return parent


    def need_group(self, content, parent):
        result = False
        node = None
        grpId = content.get("groupTag", "")
        if grpId in self.groups:
            result = True
            label, node = self.groups[grpId]
            if node is None:
                node = parent.add(type="group", label=label)
                self.groups[grpId] = (label, node)
        return result, node

    def parse(self, pathname, source, canvasid=0):
        op_branch = self.elements.op_branch
        elem_branch = self.elements.elem_branch

        # op_branch.remove_all_children()
        # elem_branch.remove_all_children()
        root_parent = elem_branch.add(type="file", filepath=pathname)
        parent = root_parent
        handler= {
            "LINE": self.parse_line,
            "PATH": self.parse_path,
            "RECT": self.parse_rect,
            "CIRCLE": self.parse_circle,
            "BITMAP": self.parse_bitmap,
            "TEXT": self.parse_text,
        }
        try:
            xcs_data = json.load(source)
        except Exception as e:
            raise BadFileError(str(e)) from e
        if "canvas" not in xcs_data:
            raise BadFileError("No canvas found")
        idx = 0
        for canvas in xcs_data["canvas"]:
            if idx != canvasid:
                if self.channel:
                    self.channel(f"We do only support from canvas {canvasid}: ignore canvas {idx} - {canvas.get('title', '<no title>')}")
                continue
            if self.channel:
                self.channel(f"Processing canvas {idx} - {canvas.get('title', '<no title>')}")
            if "displays" not in canvas:
                if self.channel:
                    self.channel("Strange, no displays found")
                continue
            self.fill_groups(canvas)
            # Displays are the elements
            displays = canvas["displays"]
            for disp in displays:
                mode = disp.get("type", "")
                mode = mode.upper()
                if self.channel:
                    self.channel(f"Loading {mode}")
                if mode in handler:
                    handler[mode](parent=parent, content=disp)
                else:
                    self.parse_unknown(parent=parent, content=disp)
                # pprint (disp)
            idx += 1
        root_parent.focus()

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        loader = XCSLoader(context=context, elements=elements_service)
        with open(pathname, "r") as source:
            loader.parse(pathname, source, canvasid=0)
        # try:
        #     with open(pathname, "r") as source:
        #         loader.parse(pathname, source, canvasid=0)
        # except (IOError, IndexError) as e:
        #     raise BadFileError(str(e)) from e
        elements_service._loading_cleared = True
        return True


