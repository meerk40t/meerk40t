import os
from meerk40t.svgelements import Color, Matrix, Path
from meerk40t.kernel.kernel import get_safe_path
from meerk40t.tools.geomstr import Geomstr
"""
vracer routines, 
https://github.com/visioncortex/vtracer
"""


def plugin(kernel, lifecycle=None):
    if lifecycle == "invalidate":
        try:
            import vtracer
        except ImportError:
            # print("Potrace plugin could not load because potracer/pypotrace is not installed.")
            return True

    if lifecycle == "register":
        _ = kernel.translation
        import vtracer

        def make_vector(
            image,
            colormode = 'binary',        # ["color"] or "binary"
            hierarchical = 'stacked',   # ["stacked"] or "cutout"
            mode = 'spline',            # ["spline"] "polygon", or "none"
            filter_speckle = 4,         # default: 4
            color_precision = 6,        # default: 6
            layer_difference = 16,      # default: 16
            corner_threshold = 60,      # default: 60
            length_threshold = 4.0,     # in [3.5, 10] default: 4.0
            max_iterations = 10,        # default: 10
            splice_threshold = 45,      # default: 45
            path_precision = 8,          # default: 8        
            **kwargs,
        ):
            if colormode is None or colormode not in ("color", "binary"):
                colormode = "binary"
            if mode is None or mode not in ("spline", "polygon"):
                mode = "spline"
            if hierarchical is None or hierarchical not in ("hierarchical", "cutout"):
                hierarchical = "hierarchical"
            if filter_speckle is None:
                filter_speckle = 4
            if color_precision is None:
                color_precision = 6
            if layer_difference is None:
                layer_difference = 16
            if corner_threshold is None:
                corner_threshold = 60
            if length_threshold is None or length_threshold < 3.5 or length_threshold>10:
                length_threshold = 4
            if max_iterations is None:
                max_iterations = 10
            if splice_threshold is None:
                splice_threshold = 45
            if path_precision is None:
                path_precision = 8
            image = image.convert("RGBA")
            pixels: list[tuple[int, int, int, int]] = list(image.getdata())
            svg = vtracer.convert_pixels_to_svg(
                size = (image.width, image.height),
                rgba_pixels = pixels,
                colormode = colormode,
                hierarchical = hierarchical,
                mode = mode,
                filter_speckle = filter_speckle,         # default: 4
                color_precision = color_precision,        # default: 6
                layer_difference = layer_difference,      # default: 16
                corner_threshold = corner_threshold,      # default: 60
                length_threshold = length_threshold,     # in [3.5, 10] default: 4.0
                max_iterations = max_iterations,        # default: 10
                splice_threshold = splice_threshold,      # default: 45
                path_precision = path_precision          # default: 8
            )
            return svg

        kernel.register("render-op/make_vector2", make_vector)

        @kernel.console_option(
            "color",
            "C",
            type=Color,
            help=_("set foreground color (default Black)"),
        )
        @kernel.console_option("original", "o", type=bool, action="store_true")
        @kernel.console_command(
            "vtrace",
            help=_("return paths around image"),
            input_type=("image", None),
            output_type=None,
        )
        def do_vtrace(
            command, 
            channel, 
            _,             
            data=None,
            color=None,
            original=False,
            **kwargs,
        ):
            elements = kernel.root.elements
            if data is None:
                data = [node for node in elements.flat(emphasized=True) if hasattr(node, "active_image")]
            if len(data) == 0:
                channel("No image selected")
            if color is None:
                color = Color("black")

            for node in data:
                bb = node.bounds
                image = node.active_image
                if original:
                    iw = node.image.width
                    ih = node.image.height
                    aw = image.width
                    ah = image.height
                    dx = (bb[2] - bb[0]) * iw / aw
                    dy = (bb[3] - bb[1]) * ih / ah
                    bb = (bb[0], bb[1], bb[0] + dx, bb[1] + dy )
                    image = node.image
                channel(f"Processing {'original' if original else 'modified'} image with {image.width}x{image.height} pixels")
                svgdata = make_vector(
                    image=image,
                )
                directory = get_safe_path(kernel.name, create=True)
                filename = os.path.join(directory, "vtrace_temp.svg")
                with open(filename, "w") as f:
                    f.write(svgdata)
                # Now load the data
                kernel.elements(f'xload "{filename}" {bb[0]} {bb[1]} {bb[2] - bb[0]} {bb[3] - bb[1]}\n')

