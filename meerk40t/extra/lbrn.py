"""
Parser for .lbrn Lightburn files.

Lightburn files are xml files denoting simple types with a narrowly nested style. They come in two main flavors,
.lbrn and .lbrn2 files, the latter of which has a bit of optimization for loading efficiency.

"""
import base64
from io import BytesIO
from xml.etree.ElementTree import iterparse

import PIL.Image

from meerk40t.core.exceptions import BadFileError
from meerk40t.core.units import UNITS_PER_INCH, UNITS_PER_MM
from meerk40t.svgelements import Color, Matrix, Path, Polygon


def plugin(kernel, lifecycle):
    if lifecycle == "boot":
        context = kernel.root
    elif lifecycle == "register":
        kernel.register("load/LbrnLoader", LbrnLoader)
        pass
    elif lifecycle == "shutdown":
        pass


class LbFile:
    """
    Parse the LbrnFile given file as a stream.
    """

    def __init__(self, source):
        self.objects = []
        self.variable_text = None
        self.app_version = None
        self.format = None
        self.material_height = None
        self.mirror_x = None
        self.mirror_y = None
        parent = None  # Root Node
        children = list()

        for event, elem in iterparse(source, events=("start", "end")):
            if event == "start":
                siblings = children
                parent = (parent, children)
                children = list()
                node = (elem, children)
                siblings.append(node)
                if elem.tag == "LightBurnProject":
                    self.app_version = elem.attrib.get("AppVersion")
                    self.format = elem.attrib.get("FormatVersion")
                    self.material_height = elem.attrib.get("MaterialHeight")
                    self.mirror_x = elem.attrib.get("MirrorX")
                    self.mirror_y = elem.attrib.get("MirrorY")
                    continue
                elif elem.tag == "Thumbnail":
                    self.thumb_source_data = base64.b64decode(elem.attrib.get("Source"))
                    stream = BytesIO(self.thumb_source_data)
                    image = PIL.Image.open(stream)
                    self.objects.append(image)
                # print(f"{event}, {elem}")
            elif event == "end":
                parent, children = parent
                if elem.tag == "VariableText":
                    values = {"tag": elem.tag}
                    for c, c_children in children:
                        values[c.tag] = c.attrib.get("Value")
                    self.objects.append(values)
                elif elem.tag == "UIPrefs":
                    values = {"tag": elem.tag}
                    for c, c_children in children:
                        values[c.tag] = c.attrib.get("Value")
                    self.objects.append(values)
                elif elem.tag == "CutSetting":
                    values = {"tag": elem.tag, "type": elem.attrib.get("Type")}
                    for c, c_children in children:
                        values[c.tag] = c.attrib.get("Value")
                    self.objects.append(values)
                elif elem.tag == "XForm":
                    self.objects.append(Matrix(*map(float, elem.text.split(" "))))
                elif elem.tag == "Shape":
                    shape_type = elem.attrib.get("Type")
                    values = {"tag": elem.tag, "type": shape_type}
                    values.update(elem.attrib)
                    self.objects.append(values)
                elif elem.tag == "VertList":
                    self.objects.append(elem.text)
                elif elem.tag == "Notes":
                    values = {"tag": elem.tag}
                    values.update(elem.attrib)
                    self.objects.append(values)
                else:
                    print(f"{event}, {elem}")


class LbrnLoader:
    @staticmethod
    def load_types():
        yield "LightBurn Files", ("lbrn", "lbrn2"), "application/x-lbrn"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        try:
            with open(pathname, "r") as file:
                lbfile = LbFile(file)
        except (IOError, IndexError) as e:
            raise BadFileError(str(e)) from e

        lb_processor = LightBurnProcessor(elements_service)
        lb_processor.process(lbfile, pathname)
        return True


class LightBurnProcessor:
    def __init__(self, elements):
        self.elements = elements
        self.element_list = list()
        self.regmark_list = list()
        self.pathname = None
        self.regmark = self.elements.reg_branch
        self.op_branch = elements.op_branch
        self.elem_branch = elements.elem_branch

        self.width = elements.device.unit_width
        self.height = elements.device.unit_height
        self.cx = self.width / 2.0
        self.cy = self.height / 2.0
        self.matrix = Matrix.scale(UNITS_PER_MM, -UNITS_PER_MM)
        self.matrix.post_translate(self.cx, self.cy)

    def process(self, lb, pathname):
        print(lb.objects)
        self.op_branch.remove_all_children()
        self.elem_branch.remove_all_children()
        self.pathname = pathname
        file_node = self.elem_branch.add(type="file", filepath=pathname)
        file_node.focus()
        for f in lb.objects:
            self.parse(lb, f, file_node, self.op_branch)

    def parse(self, lb_file, element, elem, op):
        pass
