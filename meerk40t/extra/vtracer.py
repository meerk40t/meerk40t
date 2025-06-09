"""
Vtracer https://github.com/visioncortex/vtracer
visioncortex VTracer is an open source software to convert raster images (like jpg & png)
into vector graphics (svg). It can vectorize graphics and photographs and trace the curves
to output compact vector files.
Comparing to [Potrace](http://potrace.sourceforge.net/) which only accept binarized
inputs (Black & White pixmap), VTracer has an image processing pipeline which
can handle colored high resolution scans.
Comparing to Adobe Illustrator's [Image Trace](https://helpx.adobe.com/illustrator/using/image-trace.html),
VTracer's output is much more compact (less shapes) as we adopt a stacking strategy
and avoid producing shapes with holes.
A technical description of the algorithm is on [visioncortex.org/vtracer-docs](//www.visioncortex.org/vtracer-docs).
To use it we need to have the python interface in place: pip install vtracer
"""

"""
Not needed left here for reference purposes

def simplified_load(source : str, bbox : tuple) -> list:
    from meerk40t.tools.geomstr import Geomstr
    from meerk40t.svgelements import Matrix, Color
    from meerk40t.core.node.elem_path import PathNode
    from time import perf_counter
    t0 = perf_counter()
    time_geom = 0
    time_trans = 0
    time_read = 0
    time_bbox = 0
    result_list = []
    p_pattern = '<path d="'
    t_pattern = 'transform="'
    f_pattern = 'fill="'
    black = Color("black")
    content = []
    min_x = float("inf")
    min_y = float("inf")
    max_x = -float("inf")
    max_y = -float("inf")
    with open(source, "r") as svg_file:
        tt = perf_counter()
        all_lines = svg_file.readlines()
        time_read = perf_counter() - tt
        for line in all_lines:
            idx_start = line.find(p_pattern, 0)
            if idx_start < 0:
                continue
            idx_end = line.find('"', idx_start + len(p_pattern))
            d_str = line[idx_start + len(p_pattern):idx_end]
            # print (d_str)
            tt = perf_counter()
            geom = Geomstr.svg(d_str)
            time_geom += perf_counter() - tt
            if geom.index == 0:
                # print (f"Strange, empty from '{d_str}' ({line})")
                continue
            fill_value = None
            mat_start = line.find(t_pattern, idx_end)
            if mat_start >= 0:
                tt = perf_counter()
                mat_end = line.find('"', mat_start + len(t_pattern))
                mat_str = line[mat_start + len(t_pattern):mat_end]
                matrix = Matrix(mat_str)
                geom.transform(matrix)
                time_trans += perf_counter() - tt
            fill_start = line.find(f_pattern, idx_end)
            if fill_start >= 0:
                fill_end = line.find('"', fill_start + len(f_pattern))
                fill_str = line[fill_start + len(f_pattern):fill_end]
                # if fill_str == "#ffffff":
                #     continue

            else:
                fill_str = ""
            content.append((geom, fill_str))
            tt = perf_counter()
            g_bb = geom.bbox()
            min_x = min(min_x, g_bb[0])
            min_y = min(min_y, g_bb[1])
            max_x = max(max_x, g_bb[2])
            max_y = max(max_y, g_bb[3])
            time_bbox += perf_counter() - tt
    t1 = perf_counter()
    if content:
        sx = (bbox[2] - bbox[0]) / (max_x - min_x)
        sy = (bbox[3] - bbox[1]) / (max_y - min_y)
        tx = bbox[0] - min_x
        ty = bbox[1] - min_y
        components = (sx, 0, 0, sy, tx, ty)
        matrix = Matrix(components)
    else:
        matrix = None
    for geom, fill_str in content:
        if matrix:
            tt = perf_counter()
            geom.transform(matrix)
            time_trans += perf_counter() - tt
        node = PathNode(geometry = geom, stroke=black, stroke_width = 500)
        if fill_str:
            fill_value = Color(fill_str)
            node.fill = fill_value
        result_list.append(node)
    t2 = perf_counter()
    # print (f"Loading and geometry creation: {t1-t0:.2f}sec, node creation: {t2-t1:.2f} sec, total: {t2-t0:.2f}sec")
    # print (f"Pure creation: {time_geom:.2f}sec, transform {time_trans:.2f}sec, reading {time_read:.2f}sec, bbox: {time_bbox:.2f}sec")
    return result_list
"""


def plugin(kernel, lifecycle=None):
    if lifecycle == "invalidate":
        try:
            import vtracer
        except ImportError:
            # print("vtracer plugin could not load because vtracer is not installed.")
            return True

    if lifecycle == "register":
        _ = kernel.translation

        @kernel.console_command(
            "vtracer",
            help=_("return paths around image"),
            input_type=("image", "elements", None),
            output_type="elements",
        )
        def do_vtracer(
            channel,
            data=None,
            **kwargs,
        ):
            try:
                import os
                from time import perf_counter

                from vtracer import convert_image_to_svg_py

                from meerk40t.core.units import Length
                from meerk40t.kernel import get_safe_path
            except ImportError:
                channel("vtracer isn't installed, use 'pip install vtracer'")
                return None
            elements = kernel.root.elements
            if data is None:
                data = list(elements.elems(emphasized=True))
            if not data:
                channel(_("Nothing selected"))
                return
            images = [node for node in data if hasattr(node, "image")]
            if not images:
                channel(_("No images selected"))
                return

            safe_dir = os.path.realpath(get_safe_path(kernel.name))
            input_file = os.path.join(safe_dir, "_vtrace_input.png")
            output_file = os.path.join(safe_dir, "_vtrace_output.svg")
            t_start = perf_counter()
            t_convert = t_load = 0
            # _("Vectorizing image")
            with elements.undoscope("Vectorizing image"):
                for node in images:
                    # kernel.root.signal("freeze_tree", True)
                    _start = perf_counter()
                    bb = node.bounds
                    im_wd = bb[2] - bb[0]
                    im_ht = bb[3] - bb[1]
                    im_x = bb[0]
                    im_y = bb[1]
                    flag = node.prevent_crop
                    if not flag:
                        node.prevent_crop = True
                        node.update(None)
                        bb2 = node.bounds
                        dx = bb2[0] - bb[0]
                        dy = bb2[1] - bb[1]
                        bb = (bb[0] - dx, bb[1] - dy, bb[2] - dx, bb[3] - dy)
                        node.prevent_crop = flag
                        node.update(None)
                    image = node.image

                    image.save(input_file)
                    convert_image_to_svg_py(
                        image_path=input_file, out_path=output_file, colormode="binary"
                    )
                    t_convert += perf_counter() - _start

                    _start = perf_counter()
                    # print (f"Vectorization took {t1-t0:.1f}sec, now loading file, executing {cmd}")
                    elements.suppress_updates = True
                    cmd = (
                        f'xload "{output_file}"'
                        + f" {Length(im_x).length_mm}"
                        + f" {Length(im_y).length_mm}"
                        f" {Length(im_wd).length_mm}" + f" {Length(im_ht).length_mm}"
                    )
                    kernel.root(f"{cmd}\n")
                    # elements.suppress_updates = True
                    # nodes = simplified_load(output_file, bb)
                    # elem = kernel.elements.elem_branch.add(type="group", label=f"VTrace ({node.display_label()})")
                    # for e in nodes:
                    #     elem.add_node(e)
                    # elements.suppress_updates = False
                    t_load += perf_counter() - _start
                    try:
                        os.remove(input_file)
                        os.remove(output_file)
                    except (PermissionError, OSError):
                        pass
                    except Exception as e:
                        channel(f"Could not remove temporary files: {e}")
                    # kernel.root.signal("freeze_tree", False)
            t_end = perf_counter()
            channel(
                _(
                    "Time needed for vectorisation: {time_total}sec (analysis: {time_convert}sec, loading: {time_load}sec)"
                ).format(
                    time_total=round(t_end - t_start, 1),
                    time_convert=round(t_convert, 1),
                    time_load=round(t_load, 1),
                )
            )
            kernel.root.signal("refresh_scene", "Scene")
            return "elements", None
