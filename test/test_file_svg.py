import os
import unittest
from test import bootstrap

from meerk40t.core.node.op_engrave import EngraveOpNode
from meerk40t.core.units import Length


class TestFileSVG(unittest.TestCase):
    def test_load_save_svg(self):
        """
        test svg saving and loading of various files.
        """
        file1 = "test.svg"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("operation* delete\n")
            node = EngraveOpNode(
                id="E1",
                label="My label",
                color="green",
                lock=True,
                allowed_attributes=["number_of_unicorns"],
                stroke="green",
                fill="gray",
                stroke_width=7,
                dancing_bear=0.2,
            )
            kernel.elements.op_branch.add_node(node)
            kernel.console(f"rect 2cm 2cm 1cm 1cm engrave -s 15\n")
            kernel.console(f"save {file1}\n")
            kernel.console("element* delete\n")
            kernel.console("operation* delete\n")
            kernel.console(f"load {file1}\n")
            f = list(kernel.elements.elem_branch.flat(types="elem rect"))[0]
            self.assertEqual(f.width, float(Length("1cm")))

            ns = list(kernel.elements.op_branch.flat(types="op engrave"))
            node_copy = ns[0]
            for attr in (
                "id",
                "label",
                "color",
                "lock",
                "allowed_attributes",
                "stroke",
                "fill",
                "stroke_width",
                "stroke_scaled",
            ):
                if hasattr(node, attr):
                    self.assertEqual(getattr(node_copy, attr), getattr(node, attr))
            self.assertEqual(node_copy.settings["dancing_bear"], 0.2)
            for item in node.settings:
                self.assertEqual(node.settings[item], node_copy.settings[item])
            print(f)

        finally:
            kernel()

    def test_load_save_svg_int_id(self):
        """
        tests that the validation of id prevents integer value.
        """
        file1 = "test.svg"
        self.addCleanup(os.remove, file1)

        kernel = bootstrap.bootstrap()
        try:
            kernel.console("operation* delete\n")
            node = EngraveOpNode(id="1", label="1", speed=39.8)
            kernel.elements.op_branch.add_node(node)
            kernel.console(f"save {file1}\n")
            kernel.console("operation* delete\n")
            kernel.console(f"load {file1}\n")
            node_copy = list(kernel.elements.op_branch.flat(types="op engrave"))[0]
            self.assertEqual(node_copy.id, node.id)
            self.assertIsInstance(node_copy.id, str)

            self.assertEqual(node_copy.label, node.label)
            self.assertIsInstance(node_copy.label, str)

            self.assertEqual(node_copy.speed, node.speed)
            self.assertIsInstance(node_copy.speed, float)
        finally:
            kernel()

    def test_load_092_operations(self):
        """
        test to ensure that `meerk40t:operation` types load.
        """
        file1 = "test-ops.svg"
        self.addCleanup(os.remove, file1)
        with open(file1, "w") as f:
            f.write(
                """
            <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:meerk40t="https://github.com/meerk40t/meerk40t/wiki/Namespace" width="400.0mm" height="430.0mm" viewBox="0 0 1032047 1109450">
            <meerk40t:operation type="op raster" lock="False" speed="150.0" dpi="500" color="black" frequency="30.0" stopop="False" allowed_attributes="[]" power="1000" dwell_time="50.0" id="meerk40t:3" />
            <meerk40t:operation type="op engrave" label="Engrave (100%, 20mm/s)" lock="False" id="E1" speed="20" power="1000" allowed_attributes="['stroke']" color="#0000ff00" dangerous="False" output="True" dwell_time="50.0" references="meerk40t:6" />
            <meerk40t:operation type="op cut" label="Cut (100%, 1mm/s)" lock="False" speed="1.0" color="#ff000000" frequency="30.0" kerf="0" allowed_attributes="['stroke']" power="1000" dwell_time="50.0" id="C1" />
            <ellipse cx="550118.9389283657" cy="363374.1254904113" rx="96436.11909338088" ry="96436.11909338088" stroke_scale="False" type="elem ellipse" id="meerk40t:6" lock="False" mkparam="('circle', 0, 550118.9389283657, 363374.1254904113, 0, 618309.5726906088, 295183.49172816816)" vector-effect="non-scaling-stroke" fill-rule="evenodd" stroke="#0000ff" stroke-width="1000.0" fill="none" />
            </svg>"""
            )

        kernel = bootstrap.bootstrap()
        try:
            ob = kernel.elements.op_branch
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console(f"load {file1}\n")
            self.assertEqual(len(list(ob.flat(types="op raster"))), 1)
            self.assertEqual(len(list(ob.flat(types="op engrave"))), 1)
            self.assertEqual(len(list(ob.flat(types="op cut"))), 1)
        finally:
            kernel()

    def test_load_hatch_op(self):
        """
        test to ensure that `meerk40t:operation` op hatch loading.
        """
        file1 = "test-hatch.svg"
        self.addCleanup(os.remove, file1)
        with open(file1, "w") as f:
            f.write(
                """
            <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:meerk40t="https://github.com/meerk40t/meerk40t/wiki/Namespace" width="400.0mm" height="430.0mm" viewBox="0 0 1032047 1109450">
            <meerk40t:operation type="op hatch" label="Engrave (100%, 20mm/s)" lock="False" id="E1" speed="20" power="1000" allowed_attributes="['stroke']" color="#0000ff00" dangerous="False" output="True" dwell_time="50.0" references="meerk40t:6" />
            </svg>"""
            )

        kernel = bootstrap.bootstrap()
        try:
            ob = kernel.elements.op_branch
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console(f"load {file1}\n")
            self.assertEqual(len(list(ob.flat(types="op raster"))), 0)
            self.assertEqual(len(list(ob.flat(types="op engrave"))), 1)
            self.assertEqual(len(list(ob.flat(types="op cut"))), 0)
            self.assertEqual(len(list(ob.flat(types="effect hatch"))), 1)
        finally:
            kernel()

    def test_load_wobble(self):
        """
        test to ensure that `meerk40t:operation` types load.
        """
        file1 = "test-wobble.svg"
        self.addCleanup(os.remove, file1)
        with open(file1, "w") as f:
            f.write(
                """
            <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:ev="http://www.w3.org/2001/xml-events" xmlns:meerk40t="https://github.com/meerk40t/meerk40t/wiki/Namespace" width="400.0mm" height="430.0mm" viewBox="0 0 1032047 1109450">
            <g type="op engrave" label="Engrave (100%, 20mm/s)" lock="False" id="E1" speed="20" power="1000" allowed_attributes="['stroke']" color="#0000ff00" dangerous="False" output="True" dwell_time="50.0" references="meerk40t:6">
            <g type="effect wobble" lock="False" output="True" />
            </g>
            <ellipse cx="550118.9389283657" cy="363374.1254904113" rx="96436.11909338088" ry="96436.11909338088" stroke_scale="False" type="elem ellipse" id="meerk40t:6" lock="False" mkparam="('circle', 0, 550118.9389283657, 363374.1254904113, 0, 618309.5726906088, 295183.49172816816)" vector-effect="non-scaling-stroke" fill-rule="evenodd" stroke="#0000ff" stroke-width="1000.0" fill="none" />
            </svg>"""
            )

        kernel = bootstrap.bootstrap()
        try:
            ob = kernel.elements.op_branch
            kernel.console("operation* delete\n")
            kernel.console("element* delete\n")
            kernel.console(f"load {file1}\n")
            self.assertEqual(len(list(ob.flat(types="op raster"))), 0)
            engrave = list(ob.flat(types="op engrave"))
            self.assertEqual(len(engrave), 1)
            self.assertEqual(len(list(ob.flat(types="op cut"))), 0)
            self.assertEqual(len(list(ob.flat(types="effect wobble"))), 1)
            self.assertEqual(len(list(engrave[0].flat(types="effect wobble"))), 1)
        finally:
            kernel()
