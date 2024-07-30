from meerk40t.core.node.blobnode import BlobNode
from meerk40t.core.node.branch_elems import BranchElementsNode
from meerk40t.core.node.branch_ops import BranchOperationsNode
from meerk40t.core.node.branch_regmark import BranchRegmarkNode
from meerk40t.core.node.cutnode import CutNode
from meerk40t.core.node.effect_hatch import HatchEffectNode
from meerk40t.core.node.effect_warp import WarpEffectNode
from meerk40t.core.node.effect_wobble import WobbleEffectNode
from meerk40t.core.node.elem_ellipse import EllipseNode
from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_line import LineNode
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.elem_point import PointNode
from meerk40t.core.node.elem_polyline import PolylineNode
from meerk40t.core.node.elem_rect import RectNode
from meerk40t.core.node.elem_text import TextNode
from meerk40t.core.node.filenode import FileNode
from meerk40t.core.node.groupnode import GroupNode
from meerk40t.core.node.image_raster import ImageRasterNode
from meerk40t.core.node.layernode import LayerNode
from meerk40t.core.node.op_cut import CutOpNode
from meerk40t.core.node.op_dots import DotsOpNode
from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.node.op_image import ImageOpNode
from meerk40t.core.node.op_raster import RasterOpNode
from meerk40t.core.node.place_current import PlaceCurrentNode
from meerk40t.core.node.place_point import PlacePointNode
from meerk40t.core.node.refnode import ReferenceNode
from meerk40t.core.node.rootnode import RootNode
from meerk40t.core.node.util_console import ConsoleOperation
from meerk40t.core.node.util_goto import GotoOperation
from meerk40t.core.node.util_home import HomeOperation
from meerk40t.core.node.util_input import InputOperation
from meerk40t.core.node.util_output import OutputOperation
from meerk40t.core.node.util_wait import WaitOperation

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
