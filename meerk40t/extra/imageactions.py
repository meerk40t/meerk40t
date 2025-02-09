from copy import copy
from math import isinf

from meerk40t.core.node.elem_image import ImageNode
from meerk40t.core.node.elem_rect import RectNode
from meerk40t.core.node.node import Node
from meerk40t.core.units import UNITS_PER_INCH
from meerk40t.svgelements import Color, Matrix


def prepare_data(data, dsort, pop):
    """
    Prepares the elements data.

    Sorts by the emphasized time, and optionally pops the first element from the remaining elements.

    @param data:
    @param dsort:
    @param pop:
    @return:
    """
    if dsort == "first":
        data.sort(key=lambda n: n.emphasized_time)
    elif dsort == "last":
        data.sort(reverse=True, key=lambda n: n.emphasized_time)
    if pop:
        mnode = data.pop(0)
        return Node.union_bounds(data, attr="paint_bounds"), mnode
    return Node.union_bounds(data, attr="paint_bounds")


def create_image(make_raster, data, data_bounds, dpi, keep_ratio=True):
    """
    Creates the image with the make_raster command.

    @param make_raster: function to perform raster operation
    @param data: elements to render
    @param data_bounds: bounds around the data.
    @param dpi: dots per inch for the resulting image
    @param keep_ratio: should this create command be forced to keep the ratio.
    @return:
    """
    if not make_raster:
        return None, None

    if data_bounds is None:
        return None, None
    xmin, ymin, xmax, ymax = data_bounds
    if isinf(xmin):
        # No bounds for selected elements.
        return None
    width = xmax - xmin
    height = ymax - ymin

    dots_per_units = dpi / UNITS_PER_INCH
    new_width = width * dots_per_units
    new_height = height * dots_per_units
    new_height = max(new_height, 1)
    new_width = max(new_width, 1)
    try:
        image = make_raster(
            data,
            bounds=data_bounds,
            width=new_width,
            height=new_height,
            keep_ratio=keep_ratio,
        )
    except Exception:
        return None, None
    matrix = Matrix.scale(width / new_width, height / new_height)
    return image, matrix


def mask_image(elem_image, mask, matrix, dpi, dx=0, dy=0):
    """
    Masks the elem_image with the mask_image.

    @param elem_image: image to be masked
    @param mask: mask to use
    @param matrix: Matrix of the current image
    @param dpi: Requested dots per inch.
    @param dx: adjustment to position
    @param dy: adjustment to position
    @return: Created ImageNode
    """
    imagematrix = copy(matrix)
    imagematrix.post_translate(dx, dy)

    mask_pattern = mask.convert("1")
    elem_image.putalpha(mask_pattern)

    image_node1 = ImageNode(
        image=elem_image,
        matrix=imagematrix,
        dpi=dpi,
        label="Keyholed Elements",
    )
    image_node1.set_dirty_bounds()
    return [image_node1]


def split_image(elements, image, matrix, bounds, dpi, cols, rows):
    """
    Performs the split operation of render+split. Divides those elements into even sized chunks. These chunks are
    positioned where the previous rendered elements were located.

    @param elements: elements service
    @param image: image to be split
    @param matrix: matrix of the image being split
    @param bounds: bounds of the image being split
    @param dpi: dpi of the resulting images.
    @param cols:
    @param rows:
    @return:
    """
    data_out = []
    context = elements.elem_branch
    if cols != 1 or rows != 1:
        context = elements.elem_branch.add(type="group", label="Splitted Images")
        data_out.append(context)

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
            tile = image.crop((startx, starty, endx, endy))
            tilematrix = copy(matrix)
            tilematrix.post_translate(offset_x, offset_y)

            image_node = context.add(
                type="elem image", image=tile, matrix=tilematrix, dpi=dpi
            )
            data_out.append(image_node)

            startx = endx + 1
            offset_x += deltax_bound
        starty = endy + 1
        offset_y += deltay_bound
    return data_out


def plugin(kernel, lifecycle):
    if lifecycle != "register":
        return

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
        bb = prepare_data(data, order, pop=False)
        make_raster = elements.lookup("render-op/make_raster")
        image, matrix = create_image(make_raster, data, bb, dpi, keep_ratio=False)
        if image is None:
            return "elements", None

        data_out = split_image(elements, image, matrix, bb, dpi, cols, rows)
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
        "invert", "i", help=_("invert masking of image"), type=bool, action="store_true"
    )
    @kernel.console_option(
        "outline",
        "b",
        help=_("add outline of keyhole shape"),
        type=bool,
        action="store_true",
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
        invert=False,
        outline=False,
        origin=None,
        data=None,
        post=None,
        **kwargs,
    ):
        elements = context.elements
        classify_new = elements.post_classify
        if data is None:
            data = list(elements.elems(emphasized=True))
        if order is None:
            order = ""
        if dpi is None or dpi <= 0:
            dpi = 500
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
        bb, tempnode = prepare_data(data, order, pop=True)
        masknode = copy(tempnode)
        if (
            outline
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
        make_raster = elements.lookup("render-op/make_raster")
        elemimage, elemmatrix = create_image(
            make_raster, data, total_bounds, dpi, keep_ratio=True
        )
        if elemimage is None:
            return "elements", data
        maskimage, maskmatrix = create_image(
            make_raster, maskdata, total_bounds, dpi, keep_ratio=True
        )
        if maskimage is None:
            return "elements", data
        if not invert:
            from PIL import ImageOps

            maskimage = ImageOps.invert(maskimage)

        if maskimage is None or elemimage is None:
            channel(_("Intermediary images were none"))
            return "elements", None

        data_out = mask_image(
            elemimage, maskimage, elemmatrix, dpi, total_bounds[0], total_bounds[1]
        )
        for imnode in data_out:
            elements.elem_branch.add_node(imnode)
        # Newly created! Classification needed?
        post.append(classify_new(data_out))
        elements.signal("element_added", data_out)
        elements.signal("refresh_scene", "Scene")
        return "elements", data_out
