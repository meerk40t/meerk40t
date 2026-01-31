from sefrocut.core.node.blobnode import BlobNode
from sefrocut.core.node.branch_elems import BranchElementsNode
from sefrocut.core.node.branch_ops import BranchOperationsNode
from sefrocut.core.node.branch_regmark import BranchRegmarkNode
from sefrocut.core.node.cutnode import CutNode
from sefrocut.core.node.effect_hatch import HatchEffectNode
from sefrocut.core.node.effect_warp import WarpEffectNode
from sefrocut.core.node.effect_wobble import WobbleEffectNode
from sefrocut.core.node.elem_ellipse import EllipseNode
from sefrocut.core.node.elem_image import ImageNode
from sefrocut.core.node.elem_line import LineNode
from sefrocut.core.node.elem_path import PathNode
from sefrocut.core.node.elem_point import PointNode
from sefrocut.core.node.elem_polyline import PolylineNode
from sefrocut.core.node.elem_rect import RectNode
from sefrocut.core.node.elem_text import TextNode
from sefrocut.core.node.filenode import FileNode
from sefrocut.core.node.groupnode import GroupNode
from sefrocut.core.node.image_raster import ImageRasterNode
from sefrocut.core.node.layernode import LayerNode
from sefrocut.core.node.op_cut import CutOpNode
from sefrocut.core.node.op_dots import DotsOpNode
from sefrocut.core.node.op_engrave import EngraveOpNode
from sefrocut.core.node.op_image import ImageOpNode
from sefrocut.core.node.op_raster import RasterOpNode
from sefrocut.core.node.place_current import PlaceCurrentNode
from sefrocut.core.node.place_point import PlacePointNode
from sefrocut.core.node.refnode import ReferenceNode
from sefrocut.core.node.rootnode import RootNode
from sefrocut.core.node.util_console import ConsoleOperation
from sefrocut.core.node.util_goto import GotoOperation
from sefrocut.core.node.util_home import HomeOperation
from sefrocut.core.node.util_input import InputOperation
from sefrocut.core.node.util_output import OutputOperation
from sefrocut.core.node.util_wait import WaitOperation

defaults = {
    "root": {},
    "op cut": {"speed": 12.0, "color": "red", "frequency": 30.0},
    "op engrave": {"speed": 35.0, "color": "blue", "frequency": 30.0},
    "op raster": {"speed": 150.0, "dpi": 500, "color": "black", "frequency": 30.0},
    "op image": {"speed": 150.0, "color": "transparent", "frequency": 30.0},
    "op dots": {"speed": 150.0, "color": "transparent", "frequency": 30.0},
    "util console": {},
    "util wait": {},
    "util home": {},
    "util goto": {},
    "util input": {},
    "util output": {},
    "blob": {},
    "group": {},
    "layer": {},
    "elem ellipse": {},
    "elem line": {},
    "elem rect": {},
    "elem path": {},
    "elem point": {},
    "elem polyline": {},
    "elem image": {"dpi": 500},
    "elem text": {},
    "reference": {},
    "cutcode": {},
    "branch ops": {},
    "branch elems": {},
    "branch reg": {},
    "file": {},
}

bootstrap = {
    "root": RootNode,
    "op cut": CutOpNode,
    "op engrave": EngraveOpNode,
    "op raster": RasterOpNode,
    "op image": ImageOpNode,
    "op dots": DotsOpNode,
    "effect hatch": HatchEffectNode,
    "effect wobble": WobbleEffectNode,
    "effect warp": WarpEffectNode,
    "util console": ConsoleOperation,
    "util wait": WaitOperation,
    "util home": HomeOperation,
    "util goto": GotoOperation,
    "util input": InputOperation,
    "util output": OutputOperation,
    "place point": PlacePointNode,
    "place current": PlaceCurrentNode,
    "blob": BlobNode,
    "group": GroupNode,
    "layer": LayerNode,
    "elem ellipse": EllipseNode,
    "elem line": LineNode,
    "elem rect": RectNode,
    "elem path": PathNode,
    "elem point": PointNode,
    "elem polyline": PolylineNode,
    "elem image": ImageNode,
    "elem text": TextNode,
    "image raster": ImageRasterNode,
    "reference": ReferenceNode,
    "cutcode": CutNode,
    "branch ops": BranchOperationsNode,
    "branch elems": BranchElementsNode,
    "branch reg": BranchRegmarkNode,
    "file": FileNode,
}
