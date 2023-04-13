import unittest
from test import bootstrap

from meerk40t.core.cutcode.cutcode import CutCode
from meerk40t.core.cutplan import CutPlan
from meerk40t.core.node.elem_path import PathNode
from meerk40t.core.node.op_hatch import HatchOpNode
from meerk40t.svgelements import Matrix, Path


class TestHatch(unittest.TestCase):
    def test_operation_hatch(self):
        """
        Test code to ensure op hatch hasn't been broken.

        :return:
        """
        kernel = bootstrap.bootstrap()
        try:
            initial = "M 0,0 L 10000,10000 L 0,20000 Z"
            path = Path(initial)
            laserop = HatchOpNode()
            laserop.add_node(PathNode(path))
            cutplan = CutPlan("a", kernel.root)
            matrix = Matrix()
            laserop.preprocess(kernel.root, matrix, cutplan)
            cutplan.execute()
            cutcode = CutCode(laserop.as_cutobjects())
            self.assertEqual(len(cutcode), 7)
            path = list(cutcode.as_elements())
            self.assertEqual(len(path), 1)
        finally:
            kernel.shutdown()
