"""
Parser for .lbrn Lightburn files.

Lightburn files are xml files denoting simple types with a narrowly nested style. They come in two main flavors,
.lbrn and .lbrn2 files, the latter of which has a bit of optimization for loading efficiency.

"""
import base64
from io import BytesIO
from xml.etree.ElementTree import iterparse

import PIL.Image
from meerk40t.tools.geomstr import Geomstr

from meerk40t.core.exceptions import BadFileError
from meerk40t.svgelements import Matrix


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        kernel.register("load/LbrnLoader", LbrnLoader)


def geomstry_from_vert_list(vertlist):
    geomstr = Geomstr()
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

                elif elem.tag == "XForm":
                    matrix = Matrix(*map(float, elem.text.split(" ")))

                elif elem.tag == "Shape":
                    _type = elem.attrib.get("Type")
                    values = {"tag": elem.tag, "type": _type}
                    values.update(elem.attrib)
                    if _type == "Text":
                        geometry = geomstry_from_vert_list(vertlist)
                        file_node.add(type="elem path", geometry=geometry, matrix=matrix)

                elif elem.tag == "VertList":
                    vertlist = elem.text

                elif elem.tag == "Notes":
                    values = {"tag": elem.tag}
                    values.update(elem.attrib)
                    elements.note = values.get("Notes", "")

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
