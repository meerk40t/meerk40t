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
import base64
import json
from io import BytesIO
from math import tau

import PIL.Image

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.node.node import Linejoin
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_MM, Length
from meerk40t.svgelements import Color, Matrix
from meerk40t.tools.geomstr import Geomstr

# from pprint import pprint


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("load/XCSLoaderFull", XCSLoader)
        kernel.register("load/XCSLoaderPlain", XCSLoaderPlain)

DEFAULT_SPEED = 30
DEFAULT_POWER = 30

class XCSParser:
    def __init__(self, context=None, elements=None, plain=False, *args, **kwargs):
        self.channel = context.kernel.channels["console"]
        self.context = context
        self.elements = elements
        self.groups = {}
        self.plain = plain

    def log(self, msg):
        if self.channel:
            self.channel(msg)

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

    def get_matrix(
        self,
        content,
        use_scale: bool = True,
        use_rotate: bool = True,
        use_translate: bool = True,
    ):
        x, y = self.get_coords(content)
        tx = 0
        ty = 0
        o_x = content.get("offsetX", 0)
        o_y = content.get("offsetY", 0)
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
        if use_rotate:
            angle = content.get("angle", 0)
            angle = angle / 360.0 * tau
            px, py = self.get_coords(content, "pivot")
            px += x
            py += y
        else:
            angle = 0
            px = 0
            py = 0
        skew_x, skew_y = self.get_coords(content, "skew")

        matrix = Matrix()
        # print (f"Element-type: {content['type']}, ({content['x']:.2f}, {content['y']}:.2f), w={content['width']:.2f}, h={content['height']:.2f} (center={content['x'] + content['width'] / 2:.2f}, {content['y'] + content['height'] / 2:.2f})")
        # print (f"scale={content['scale']}, pivot={content['pivot']}, angle={content['angle']}")
        # print (f"Scale required: {use_scale}, rotation required: {use_rotate}, {sx:.2f}, {sy:.2f}")
        if angle != 0:
            # print (f"Rotating: {angle / tau * 360:.2f} around ({Length(px).length_mm}, {Length(py).length_mm})")
            matrix.post_rotate(angle, px, py)
        if sx != 1 or sy != 1:
            # print (f"Scaling: {sx:.4f} / {sy:.4f} around ({Length(x).length_mm}, {Length(y).length_mm})")
            matrix.post_scale(sx=sx, sy=sy, x=x, y=y)
        if skew_x != 0 or skew_y != 0:
            self.log(f"Having skew: x={skew_x:.3f}, y={skew_y:.3f}")
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

    def get_id_and_name(self, content):
        ident = content.get("id", None)
        label = content.get("name", None)
        if label == "null":
            label = None
        return ident, label

    def get_basic_attributes(self, content):
        set_hidden = not content.get("visible", True)
        stroke = Color(content.get("layerColor", "blue"))
        lock = content.get("lockState", False)
        return set_hidden, stroke, lock

    def get_coords(self, content, key=None):
        if key:
            x_coord = self.to_length(content[key].get("x", 0))
            y_coord = self.to_length(content[key].get("y", 0))
        else:
            x_coord = self.to_length(content.get("x", 0))
            y_coord = self.to_length(content.get("y", 0))
        return x_coord, y_coord

    def parse_line(self, parent, content):
        # pprint(content)
        matrix = self.get_matrix(
            content, use_translate=False, use_scale=True, use_rotate=True
        )
        x_start, y_start = self.get_coords(content)
        x_offset = self.to_length(content.get("offsetX", 0))
        y_offset = self.to_length(content.get("offsetY", 0))
        x_end, y_end = self.get_coords(content, "endPoint")
        x_end += x_offset
        y_end += y_offset
        in_group, group_node = self.need_group(content, parent)
        ident, label = self.get_id_and_name(content)
        set_hidden, stroke, lock = self.get_basic_attributes(content)
        p_node = group_node if in_group else parent
        return p_node.add(
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

    def parse_rect(self, parent, content):
        matrix = self.get_matrix(content, use_scale=False, use_translate=False)
        x_start, y_start = self.get_coords(content)
        width = self.to_length(content.get("width", 0))
        height = self.to_length(content.get("height", 0))
        in_group, group_node = self.need_group(content, parent)
        ident, label = self.get_id_and_name(content)
        set_hidden, stroke, lock = self.get_basic_attributes(content)
        p_node = group_node if in_group else parent
        # print (f"(xcs   ) x={Length(x_start).length_mm}, y={Length(y_start).length_mm}, width={Length(width).length_mm}, height={Length(height).length_mm}")
        # print (matrix)
        return p_node.add(
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

    def get_font_attributes(self, content):
        font_style = content.get("style", {})
        font_name = "Arial"
        font_size = Length("12pt")
        if "fontSize" in font_style:
            font_size = Length(f"{font_style['fontSize']}pt")
        if "fontName" in font_style:
            font_name = font_style["fontName"]
        letter_spacing = font_style.get("letterSpacing", 0)
        alignment = font_style.get("align", "left")
        replacements = {
            "left": "start",
            "center": "middle",
            "right": "end",
        }
        if alignment in replacements:
            alignment = replacements[alignment]
        return font_name, font_size, letter_spacing, alignment

    def import_characters(self, content) -> Geomstr:
        glyph_data = content["charJSONs"]
        geom = Geomstr()
        for glyph in glyph_data:
            angle = glyph["angle"]
            dx = glyph["offsetX"]
            dy = glyph["offsetY"]
            # pprint(glyph)
            pathstr = glyph["dPath"]
            if not pathstr:
                continue
            glyph_geom = Geomstr.svg(pathstr)
            # cb = glyph_geom.bbox()
            # print (f"Text: ({content['x']:.2f}, {content['y']:.2f}), "
            #        f"char: ({glyph['x']:.2f}, {glyph['y']:.2f}), "
            #        f"char-offset: ({glyph['offsetX']:.2f}, {glyph['offsetY']:.2f}), "
            #        f"bounds=({Length(cb[0]*UNITS_PER_MM).length_mm}, {Length(cb[1]*UNITS_PER_MM).length_mm}) - ({Length(cb[2]*UNITS_PER_MM).length_mm}, {Length(cb[3]*UNITS_PER_MM).length_mm})"
            # )
            cmatrix = Matrix()
            if angle != 0:
                cmatrix.post_rotate(angle / 360 * tau)
            sx = glyph["scale"]["x"]
            sy = glyph["scale"]["x"]
            if sx != 1 or sy != 1:
                cmatrix.post_scale(sx, sy)
            cmatrix.post_translate(dx, dy)
            glyph_geom.transform(cmatrix)
            geom.append(glyph_geom, end=True)
        return geom

    def parse_text(self, parent, content):
        # We rotate and scale at character level
        matrix = Matrix()
        # x_start, y_start = self.get_coords(content)
        # width = self.to_length(content.get("width", 0))
        # height = self.to_length(content.get("height", 0))
        in_group, group_node = self.need_group(content, parent)
        ident, label = self.get_id_and_name(content)
        set_hidden, stroke, lock = self.get_basic_attributes(content)
        text_content = content.get("text", "")
        font_name, font_size, letter_spacing, alignment = self.get_font_attributes(content)

        geom = self.import_characters(content)
        geom.uscale(UNITS_PER_MM)
        # geom.translate(x_start, y_start)
        # Nothing found....
        if geom.index == 0:
            return None
        p_node = group_node if in_group else parent
        return p_node.add(
            type="elem path",
            label=label,
            id=ident,
            lock=lock,
            hidden=set_hidden,
            matrix=matrix,
            stroke=stroke,
            geometry=geom,
            linejoin=Linejoin.JOIN_MITER,
            stroke_width=500,
            mktext=text_content,
            mkfont=font_name,
            mkfontsize=font_size,
            mkalign=alignment,
        )

    def parse_path(self, parent, content):
        matrix = self.get_matrix(content, use_translate=True)
        in_group, group_node = self.need_group(content, parent)
        pathstr = content.get("dPath", None)
        if not pathstr:
            self.log("Invalid path information")
            return None
        geom = Geomstr.svg(pathstr)
        geom.uscale(UNITS_PER_MM)
        # geom.translate(x_start, y_start)
        ident, label = self.get_id_and_name(content)
        set_hidden, stroke, lock = self.get_basic_attributes(content)
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
            linejoin=Linejoin.JOIN_MITER,
            stroke_width=500,
        )
        self.fix_position(node, content)
        return node

    def parse_circle(self, parent, content):
        matrix = self.get_matrix(content, use_translate=False, use_scale=False)
        x_start, y_start = self.get_coords(content)
        width = self.to_length(content.get("width", 0))
        height = self.to_length(content.get("height", 0))
        cx = x_start + width / 2
        cy = y_start + width / 2
        in_group, group_node = self.need_group(content, parent)
        ident, label = self.get_id_and_name(content)
        set_hidden, stroke, lock = self.get_basic_attributes(content)
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
        return node

    def parse_bitmap(self, parent, content):
        if "base64" not in content:
            self.log("Unknown content for bitmap")
            return None
        rawdata = content["base64"]
        prefix = "data:image/png;base64,"
        if rawdata.startswith(prefix):
            rawdata = rawdata[len(prefix) :]
        data = base64.b64decode(rawdata)
        stream = BytesIO(data)
        image = PIL.Image.open(stream)
        matrix = self.get_matrix(content, False)
        x_start, y_start = self.get_coords(content)
        width = self.to_length(content.get("width", 0))
        height = self.to_length(content.get("height", 0))
        # We need to prescale the image first...
        imagematrix = Matrix(f"translate({x_start}, {y_start})")
        imagematrix.pre_scale(width / image.width, height / image.height)
        matrix = imagematrix * matrix
        in_group, group_node = self.need_group(content, parent)
        ident, label = self.get_id_and_name(content)
        set_hidden, stroke, lock = self.get_basic_attributes(content)
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
        return node

    def parse_unknown(self, parent, content):
        self.log(f"Unknown type {content.get('type', '??')}")
        # pprint (content)
        return None

    def get_operation_context(self, content):
        data = content.get("data", {})
        if not data:
            return None
        material_list = content.get("materialList", {})
        material_type_list = content.get("materialTypeList", {})
        data_value = data.get("value", [])
        if not data_value:
            return None
        data_id, data_content = data_value[0]
        return data_content

    def extract_operation_settings(self, map_entry, main_power):
        node_id, node_data = map_entry
        processing_type = node_data["processingType"]
        settings = node_data["data"]
        operation_information = settings.get(processing_type, {})
        material_type = operation_information.get("materialType", "")
        material_infos = operation_information.get("parameter", {})
        parameter_set = material_infos.get(material_type, {})
        power = parameter_set.get("power", main_power)
        speed = parameter_set.get("speed", 20)
        passes = parameter_set.get("repeat", 1)
        return node_id, processing_type, material_type, power, speed, passes, parameter_set


    def create_ops(self, xcs_data, nodelist) -> bool:
        anything_created = False
        content = xcs_data.get("device", None)
        if not content:
            self.log("Device information was empty, no operations created")
            return False
        opname_map = {
            "VECTOR_ENGRAVING": "op engrave",
            "VECTOR_CUTTING": "op cut",
            "FILL_VECTOR_ENGRAVING": "op raster",
            "BITMAP_ENGRAVING": "op image",
            "KNIFE_CUTTING": "op cut",
        }
        main_power = content.get("power", 100)
        data_content = self.get_operation_context(content)
        if not data_content:
            self.log("Device information detils were empty, no operations created")
            return False
        # pprint (data_content)
        data_map = data_content.get("displays", {})
        map_data = data_map.get("value", [])
        operation_list = {}
        for map_entry in map_data:
            node_id, processing_type, material_type, power, speed, passes, parameter_set = self.extract_operation_settings(map_entry, main_power)
            hash_value = f"{processing_type}-{power}-{speed}-{passes}"
            if hash_value in operation_list:
                op_node = operation_list[hash_value]
            else:
                p_node = self.elements.op_branch
                op_label = f"{material_type} - {power}%"
                if processing_type in opname_map:
                    op_type = opname_map[processing_type]
                else:
                    self.log(f"Unknown processing type: {processing_type}")
                    continue
                op_node = p_node.add(
                    type=op_type,
                    label=op_label,
                    power=power * 10,  # was given in percent
                    speed=speed,
                    passes=passes,
                )
                anything_created = True
                if op_type == "op cut":
                    kerf_distance = (
                        parameter_set.get("kerfDistance", 0)
                        if parameter_set.get("enableKerf", False)
                        else 0
                    )
                    op_node.kerf = kerf_distance
                if op_type == "op image":
                    if "density" in parameter_set:
                        op_node.overrule_dpi = True
                        op_node.dpi = parameter_set["density"]
                    if "bitmapMode" in parameter_set:
                        bmode = parameter_set["bitmapMode"]
                        # usually 'grayscale'
                operation_list[hash_value] = op_node
            if node_id in nodelist:
                cnode = nodelist[node_id]
                op_node.add_reference(cnode)
        return anything_created

    def parse(self, pathname, source, canvasid=0, **kwargs):
        elem_branch = self.elements.elem_branch

        # op_branch.remove_all_children()
        # elem_branch.remove_all_children()
        root_parent = elem_branch.add(type="file", filepath=pathname)
        parent = root_parent
        handler = {
            "LINE": self.parse_line,
            "PATH": self.parse_path,
            "RECT": self.parse_rect,
            "CIRCLE": self.parse_circle,
            "BITMAP": self.parse_bitmap,
            "TEXT": self.parse_text,
        }
        try:
            xcs_data = json.load(source)
        except OSError as e:
            raise BadFileError(str(e)) from e
        if "canvas" not in xcs_data:
            raise BadFileError("No canvas found")
        idx = 0
        for canvas in xcs_data["canvas"]:
            if idx != canvasid:
                self.log(
                    f"We do only support import from canvas {canvasid}: ignore canvas {idx} - {canvas.get('title', '<no title>')}"
                )
                continue
            self.log(f"Processing canvas {idx} - {canvas.get('title', '<no title>')}")
            if "displays" not in canvas:
                self.log("Strange, no displays found")
                continue
            self.fill_groups(canvas)
            # Displays are the elements
            displays = canvas["displays"]
            nodes = {}
            for disp in displays:
                mode = disp.get("type", "")
                mode = mode.upper()
                self.log(f"Loading {mode}")
                if mode in handler:
                    created_node = handler[mode](parent=parent, content=disp)
                else:
                    created_node = self.parse_unknown(parent=parent, content=disp)
                if created_node:
                    node_id = created_node.id
                    if node_id:
                        nodes[node_id] = created_node
                # pprint (disp)
            if not self.plain:
                had_ops = self.create_ops(xcs_data, nodes)
                if not had_ops and nodes and self.elements.classify_new:
                    self.elements.classify(list(nodes.values()))
            idx += 1

        root_parent.focus()

"""
    Load elements from a specified file in XTool Creative Space format (.xcs) into the given context.

    This static method reads a file from the provided pathname and uses an XCSLoader to parse
    its contents into the specified elements service.
    It ensures that the loading state is cleared after the operation is completed.

    Args:
        context: The context in which the loading occurs.
        elements_service: The service responsible for managing elements.
        pathname: The path to the file to be loaded.
        **kwargs: Additional keyword arguments for loading configuration.

    Returns:
        bool: True if the loading operation was successful.

    Raises:
        BadFileError: If there is an issue reading the file or parsing its contents.
"""
class XCSLoader:

    @staticmethod
    def load_types():
        yield "XTool Files", ("xcs",), "application/x-xcs"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):

        parser = XCSParser(context=context, elements=elements_service, plain=False)
        with open(pathname, "r", encoding='utf-8') as source:
            parser.parse(pathname, source, canvasid=0)
        elements_service._loading_cleared = True
        return True
class XCSLoaderPlain:

    @staticmethod
    def load_types():
        yield "XTool Files (without laser settings)", ("xcs",), "application/x-xcs"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        parser = XCSParser(context=context, elements=elements_service, plain=True)
        with open(pathname, "r", encoding='utf-8') as source:
            parser.parse(pathname, source, canvasid=0)
        elements_service._loading_cleared = True
        return True
