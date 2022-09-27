import unittest
from random import Random

from meerk40t.core.element_types import elem_nodes, op_nodes
from test import bootstrap


class TestElementClassification(unittest.TestCase):
    def test_element_classification(self):
        """
        Random Test of classifications

        :return:
        """
        random = Random()
        kernel = bootstrap.bootstrap()
        root = kernel.get_context("/")
        # root("channel print classify\n")

        def random_units():
            r = random.randint(0, 4)
            if r == 0:
                return "px"
            if r == 1:
                return ""
            if r == 2:
                return "in"
            if r == 3:
                return "mm"
            if r == 4:
                return "cm"
            print(r)
            raise ValueError()

        def random_color():
            r = random.randint(0,4)
            if r == 0:
                return f"#{random.randint(0,255):02X}{random.randint(0,255):02X}{random.randint(0,255):02X}"
            elif r == 1:
                return f"#{random.randint(0, 16):X}{random.randint(0, 16):X}{random.randint(0, 16):X}"
            else:
                operations = list(root.elements.op_branch.flat(types=op_nodes))
                if not operations:
                    return "cornflower blue"
                random_op = operations[random.randint(0, len(operations) - 1)]
                return random_op.color.hexrgb

        def random_x():
            return f"{random.random() * 10}{random_units()}"

        random_y = random_x
        random_radius = random_x

        def add_random_element():
            r = random.randint(0,1)

            if r == 0:
                root(f"circle {random_x()} {random_y()} {random_radius()} stroke {random_color()} fill {random_color()}\n")
            if r == 1:
                root(f"line {random_x()} {random_y()} {random_x()} {random_y()} stroke {random_color()} fill {random_color()}\n")

        def add_random_operation():
            r = random.randint(0,6)
            if r == 0:
                root(f"cut -c {random_color()}\n")
            if r == 1:
                root(f"raster -c {random_color()}\n")
            if r == 2:
                root(f"engrave -c {random_color()}\n")
            if r == 3:
                root(f"hatch -c {random_color()}\n")
            if r == 4:
                root(f"imageop -c {random_color()}\n")
            if r == 5:
                root(f"dots -c {random_color()}\n")
            if r == 6:
                root(f"engrave -c {random_color()}\n")

        try:
            for i in range(10):
                add_random_operation()
            for i in range(100):
                add_random_element()
            root("element* classify\n")

            results = list(root.elements.elem_branch.flat(types=elem_nodes))
            self.assertEqual(len(results), 100)
        finally:
            kernel.shutdown()
