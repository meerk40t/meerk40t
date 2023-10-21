from copy import copy
from math import isinf

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_rect import RectNode
from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH
from meerk40t.svgelements import Color, Matrix


def plugin(kernel, lifecycle):
    if lifecycle == "register":
        _ = kernel.translation
        context = kernel.root

        @kernel.console_argument("cols", type=int, help=_("Number of columns"))
        @kernel.console_argument("rows", type=int, help=_("Number of rows"))
        @kernel.console_argument("dpi", type=int, help=_("Resolution of created image"))
        @kernel.console_option(
            "order", "o", help=_("ordering selection: none, first, last"), type=str
        )
        @kernel.console_command(
            "render_split",
            help=_("render_split <columns> <rows> <dpi>")
            + "\n"
            + _("Render selected elements and split the image into multiple parts"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def render_split(
            command,
            channel,
            _,
            cols=None,
            rows=None,
            dpi=None,
            order=None,
            origin=None,
            data=None,
            post=None,
            **kwargs,
        ):
            def prepare_data(data, dsort):
                if dsort == "first":
                    data.sort(key=lambda n: n.emphasized_time)
                elif dsort == "last":
                    data.sort(reverse=True, key=lambda n: n.emphasized_time)
                bounds = Node.union_bounds(data, attr="paint_bounds")
                return bounds

            def create_image(data, data_bounds, dpi):
                make_raster = elements.lookup("render-op/make_raster")
                if not make_raster:
                    return None, None

                if data_bounds is None:
                    return None, None
                xmin, ymin, xmax, ymax = data_bounds
                if isinf(xmin):
                    # No bounds for selected elements."))
                    return None, None
                width = xmax - xmin
                height = ymax - ymin

                dots_per_units = dpi / UNITS_PER_INCH
                new_width = width * dots_per_units
                new_height = height * dots_per_units
                new_height = max(new_height, 1)
                new_width = max(new_width, 1)

                image = make_raster(
                    data,
                    bounds=data_bounds,
                    width=new_width,
                    height=new_height,
                )

                matrix = Matrix.scale(width / new_width, height / new_height)
                return image, matrix

            def split_image(image, matrix, bounds, dpi, cols, rows):
                data_out = []
                groupit = False
                if cols != 1 or rows != 1:
                    groupit = True
                    group_node = elements.elem_branch.add(
                        type="group", label="Splitted Images"
                    )
                    data_out.append(group_node)

                imgwidth, imgheight = image.size
                deltax_image = imgwidth // cols
                deltay_image = imgheight // rows

                starty = 0
                offset_y = bounds[1]
                deltax_bound = (bounds[2] - bounds[0]) / cols
                deltay_bound = (bounds[3] - bounds[1]) / rows
                for yidx in range(rows):
                    startx = 0
                    offset_x = bounds[0]
                    endy = starty + deltay_image - 1
                    if yidx == rows - 1:
                        # Just to make sure we get the residual pixels
                        endy = imgheight - 1
                    for xidx in range(cols):
                        endx = startx + deltax_image - 1
                        if xidx == cols - 1:
                            # Just to make sure we get the residual pixels
                            endx = imgwidth - 1
                        # print(
                        #     f"Image={imgwidth}x{imgheight}, Segment={xidx}:{yidx}, Box={startx},{starty}-{endx},{endy}"
                        # )
                        tile = image.crop((startx, starty, endx, endy))
                        tilematrix = copy(matrix)
                        tilematrix.post_translate(offset_x, offset_y)
                        image_node = ImageNode(image=tile, matrix=tilematrix, dpi=dpi)
                        elements.elem_branch.add_node(image_node)
                        if groupit:
                            group_node.append_child(image_node)
                        data_out.append(image_node)

                        startx = endx + 1
                        offset_x += deltax_bound
                    starty = endy + 1
                    offset_y += deltay_bound
                return data_out

            elements = context.elements
            classify_new = elements.post_classify
            if data is None:
                data = list(elements.elems(emphasized=True))
            if cols is None:
                cols = 1
            if rows is None:
                rows = cols
            if order is None:
                order = ""
            if dpi is None or dpi <= 0:
                dpi = 500
            bb = prepare_data(data, order)
            image, matrix = create_image(data, bb, dpi)
            if image is None:
                data_out = None
            else:
                data_out = split_image(image, matrix, bb, dpi, cols, rows)
            if data_out is not None:
                # Newly created! Classification needed?
                post.append(classify_new(data_out))
                elements.signal("element_added", data_out)
                elements.signal("refresh_scene", "Scene")
            return "elements", data_out

        @kernel.console_argument("dpi", type=int, help=_("Resolution of created image"))
        @kernel.console_option(
            "order", "o", help=_("ordering selection: none, first, last"), type=str
        )
        @kernel.console_option(
            "invert", "i", help=_("invert masking of image"), type=int
        )
        @kernel.console_option(
            "outline", "o", help=_("add outline of keyhole shape"), type=int
        )
        @kernel.console_command(
            "render_keyhole",
            help=_("render_keyhole <columns> <rows> <dpi>")
            + "\n"
            + _("Render selected elements and split the image into multiple parts"),
            input_type=(None, "elements"),
            output_type="elements",
        )
        def render_keyhole(
            command,
            channel,
            _,
            dpi=None,
            order=None,
            invert=None,
            outline=None,
            origin=None,
            data=None,
            post=None,
            **kwargs,
        ):
            def prepare_data(dsort):
                # def debug_data(msg):
                #     print (f"{msg}")
                #     for idx, node in enumerate(data):
                #         print (f"{idx} - {node.type}")

                if dsort == "first":
                    data.sort(key=lambda n: n.emphasized_time)
                elif dsort == "last":
                    data.sort(reverse=True, key=lambda n: n.emphasized_time)
                mnode = data[0]
                data.pop(0)
                bounds = Node.union_bounds(data, attr="paint_bounds")
                return bounds, mnode

            def create_image(data, data_bounds, dpi):
                make_raster = elements.lookup("render-op/make_raster")
                if not make_raster:
                    return None, None

                if data_bounds is None:
                    return None, None
                xmin, ymin, xmax, ymax = data_bounds
                if isinf(xmin):
                    # No bounds for selected elements."))
                    return None
                width = xmax - xmin
                height = ymax - ymin

                dots_per_units = dpi / UNITS_PER_INCH
                new_width = width * dots_per_units
                new_height = height * dots_per_units
                new_height = max(new_height, 1)
                new_width = max(new_width, 1)

                image = make_raster(
                    data,
                    bounds=data_bounds,
                    width=new_width,
                    height=new_height,
                    keep_ratio=True,
                )
                matrix = Matrix.scale(width / new_width, height / new_height)
                return image, matrix

            def mask_image(elem_image, mask_image, matrix, bbounds, dpi):
                offset_x = bbounds[0]
                offset_y = bbounds[1]
                data_out = None
                # elem_image.convert("RGBA")
                imagematrix0 = copy(matrix)
                dx = offset_x - imagematrix0.value_trans_x()
                dy = offset_y - imagematrix0.value_trans_y()
                imagematrix0.post_translate(offset_x, offset_y)
                imagematrix1 = copy(imagematrix0)

                mask_pattern = mask_image.convert("1")
                elem_image.putalpha(mask_pattern)

                image_node1 = ImageNode(
                    image=elem_image,
                    matrix=imagematrix1,
                    dpi=dpi,
                    label="Keyholed Elements",
                )
                image_node1.set_dirty_bounds()
                elements.elem_branch.add_node(image_node1)

                # image_node2 = ImageNode(image=mask_image, matrix=imagematrix2, dpi=dpi)
                # image_node2.set_dirty_bounds()
                # image_node2.label = "Mask"
                # elements.elem_branch.add_node(image_node2)
                data_out = [image_node1]
                return data_out

            elements = context.elements
            classify_new = elements.post_classify
            if data is None:
                data = list(elements.elems(emphasized=True))
            if order is None:
                order = ""
            if dpi is None or dpi <= 0:
                dpi = 500
            if invert is None or invert == 0:
                invert = False
            invert = bool(invert)
            # channel(f"will sort by {order}")
            total_bounds = Node.union_bounds(data, attr="paint_bounds")
            rectnode = RectNode(
                x=total_bounds[0],
                y=total_bounds[1],
                width=total_bounds[2] - total_bounds[0],
                height=total_bounds[3] - total_bounds[1],
                stroke=None,
                fill=None,
            )
            bb, tempnode = prepare_data(order)
            masknode = copy(tempnode)
            if (
                outline is not None
                and outline != 0
                and tempnode.type not in ("elem text", "elem image")
                and hasattr(tempnode, "stroke")
            ):
                outlinenode = copy(tempnode)
                if hasattr(outlinenode, "fill"):
                    outlinenode.fill = None
                outlinenode.stroke = Color("black")
                outlinenode.altered()
                data.append(outlinenode)

            # Make sure they have the right size by adding a dummy node to it...
            maskdata = (masknode, rectnode)
            data.append(rectnode)

            if hasattr(masknode, "fill"):
                masknode.fill = Color("black")
            if hasattr(masknode, "stroke"):
                masknode.stroke = Color("black")
                masknode.altered()
            elemimage, elemmatrix = create_image(data, total_bounds, dpi)
            maskimage, maskmatrix = create_image(maskdata, total_bounds, dpi)
            if not invert:
                from PIL import ImageOps

                maskimage = ImageOps.invert(maskimage)

            if maskimage is None or elemimage is None:
                channel(_("Intermediary images were none"))
                data_out = None
            else:
                data_out = mask_image(
                    elemimage, maskimage, elemmatrix, total_bounds, dpi
                )
            if data_out is not None:
                # Newly created! Classification needed?
                post.append(classify_new(data_out))
                elements.signal("element_added", data_out)
                elements.signal("refresh_scene", "Scene")
            return "elements", data_out
