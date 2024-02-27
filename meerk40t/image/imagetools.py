import os
import subprocess
from copy import copy

from meerk40t.kernel import CommandSyntaxError

from ..core.exceptions import BadFileError
from ..core.units import DEFAULT_PPI, UNITS_PER_PIXEL, Angle
from ..svgelements import Color, Matrix, Path
from ..tools.geomstr import Geomstr
from .dither import dither


def plugin(kernel, lifecycle=None):
    """
    ImageTools mostly provides the image functionality to the console. It should be loaded in the root context.
    This functionality will largely depend on PIL/Pillow for the image command subfunctions.
    """

    if lifecycle == "preregister":
        kernel.register("raster_script/Gold", RasterScripts.raster_script_gold())
        kernel.register("raster_script/Stipo", RasterScripts.raster_script_stipo())
        kernel.register("raster_script/Gravy", RasterScripts.raster_script_gravy())
        kernel.register("raster_script/Xin", RasterScripts.raster_script_xin())
        kernel.register("raster_script/Newsy", RasterScripts.raster_script_newsy())
        kernel.register("raster_script/Simple", RasterScripts.raster_script_simple())
    if lifecycle != "register":
        return
    _ = kernel.translation
    kernel.register("load/ImageLoader", ImageLoader)
    choices = [
        {
            "attr": "image_dpi",
            "object": kernel.elements,
            "default": True,
            "type": bool,
            "label": _("Image DPI Scaling"),
            "tip": "\n".join(
                (
                    _("Unset: Use the image as if it were 1000 pixels per inch."),
                    _(
                        "Set: Use the DPI setting saved in the image to scale the image to the correct size."
                    ),
                )
            ),
            "page": "Input/Output",
            "section": "Input",
        },
        {
            "attr": "create_image_group",
            "object": kernel.elements,
            "default": True,
            "type": bool,
            "label": _("Create a file-node for imported image"),
            "tip": "\n".join(
                (
                    _("Unset: Attach the image directly to elements."),
                    _("Set: Put the image under a file-node created for it."),
                )
            ),
            "page": "Input/Output",
            "section": "Input",
        },
    ]
    kernel.register_choices("preferences", choices)

    context = kernel.root

    def update_image_node(node):
        if hasattr(node, "node"):
            node.node.altered()
        node.altered()
        node.update(context)

    @context.console_command(
        "image",
        help=_("image <operation>*"),
        input_type=(None, "image-array", "inkscape"),
        output_type="image",
    )
    def image(command, channel, _, data_type=None, data=None, remainder=None, **kwargs):
        elements = context.elements
        if data_type is None:
            if not remainder:
                # No additional data just list the images.
                channel(_("----------"))
                channel(_("Images:"))
                i = 0
                for node in elements.elems():
                    if node.type != "elem image":
                        continue
                    name = str(node)
                    if len(name) > 50:
                        name = name[:50] + "..."
                    channel(
                        f"{i}: ({node.image.width}, {node.image.height}) {node.image.mode}, {name}"
                    )
                    i += 1
                channel(_("----------"))
                return
            # We have additional commands, return selected images.
            if not elements.has_emphasis():
                channel(_("No selected images."))
                return
            images = [
                e for e in elements.elems(emphasized=True) if e.type == "elem image"
            ]
            return "image", images

        if data_type == "inkscape":
            # Inkscape type convert to added image.
            inkscape_path, filename = data
            if filename is None:
                channel(_("File was not set."))
                return
            if filename.endswith("png"):
                from PIL import Image

                img = Image.open(filename)
                inode = elements.elem_branch.add(image=img, type="elem image")
                return "image", [inode]
        elif data_type == "image-array":
            # Camera Image-Array, convert to image.
            from PIL import Image

            width, height, frame = data
            img = Image.fromarray(frame)
            images = [elements.elem_branch.add(image=img, type="elem image")]
            return "image", images
        else:
            raise CommandSyntaxError

    @context.console_command(
        "path",
        help=_("return paths around image"),
        input_type="image",
        output_type="elements",
    )
    def image_path(data, **kwargs):
        elements = context.elements
        paths = []
        for inode in data:
            bounds = inode.bounds
            p = Path()
            p.move(
                (bounds[0], bounds[1]),
                (bounds[0], bounds[3]),
                (bounds[2], bounds[3]),
                (bounds[2], bounds[1]),
            )
            p.closed()
            paths.append(p)
            elements.elem_branch.add(p, type="elem path")
        return "elements", paths

    @context.console_argument("script", help=_("script to apply"), type=str)
    @context.console_command(
        "wizard",
        help=_("apply image wizard"),
        input_type="image",
        output_type="elements",
    )
    def image_wizard(command, channel, _, data, script, **kwargs):
        if script is None:
            try:
                for script_name in context.match("raster_script", suffix=True):
                    channel(_("Raster Script: {name}").format(name=script_name))
            except KeyError:
                channel(_("No Raster Scripts Found."))
            return

        script = context.lookup("raster_script", script)
        if script is None:
            channel(_("Raster Script {name} is not registered.").format(name=script))
            script = []

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            if not len(script) and inode.operations:
                channel(_("Disabled raster script."))
            inode.operations = script
            inode.update(context)
        return "image", data

    @context.console_command(
        "unlock",
        help=_("unlock manipulations"),
        input_type="image",
        output_type="image",
    )
    def image_unlock(command, channel, _, data, **kwargs):
        channel(_("Unlocking Elements..."))
        for inode in data:
            try:
                if inode.lock:
                    channel(_("Unlocked: {name}").format(name=str(inode)))
                    inode.lock = False
                else:
                    channel(_("Element was not locked: {name}").format(name=str(inode)))
            except AttributeError:
                channel(_("Element was not locked: {name}").format(name=str(inode)))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_command(
        "lock",
        help=_("lock manipulations"),
        input_type="image",
        output_type="image",
    )
    def image_lock(command, channel, _, data, **kwargs):
        channel(_("Locking Elements..."))
        for inode in data:
            try:
                if not inode.lock:
                    channel(f"Locked: {str(inode)}")
                    inode.lock = True
                else:
                    channel(
                        _("Element was not unlocked: {name}").format(name=str(inode))
                    )
            except AttributeError:
                channel(_("Element was not unlocked: {name}").format(name=str(inode)))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_argument("threshold_max", type=float)
    @context.console_argument("threshold_min", type=float)
    @context.console_command(
        "threshold", help="", input_type="image", output_type="image"
    )
    def image_threshold(
        command, channel, _, data, threshold_max=None, threshold_min=None, **kwargs
    ):
        if threshold_min is None:
            raise CommandSyntaxError
        threshold_min, threshold_max = min(threshold_min, threshold_max), max(
            threshold_max, threshold_min
        )
        divide = (threshold_max - threshold_min) / 255.0
        for node in data:
            if node.lock:
                channel(_("Can't modify a locked image: {name}").format(name=str(node)))
                continue

            img = node.opaque_image
            img = img.convert("L")

            def thresh(g):
                if threshold_min >= g:
                    return 0
                elif threshold_max < g:
                    return 255
                else:  # threshold_min <= grey < threshold_max
                    value = g - threshold_min
                    value *= divide
                    return int(round(value))

            lut = [thresh(g) for g in range(256)]
            img = img.point(lut)

            elements = context.elements
            node = elements.elem_branch.add(
                image=img, type="elem image", matrix=copy(node.matrix)
            )
            elements.classify([node])
        return "image", data

    # @context.console_command(
    #     "resample", help=_("Resample image"), input_type="image", output_type="image"
    # )
    # def image_resample(data, **kwargs):
    #     for node in data:
    #         node.make_actual()
    #     return "image", data

    @context.console_option("method", "m", type=str, default="Floyd-Steinberg")
    @context.console_command(
        "dither", help=_("Dither to 1-bit"), input_type="image", output_type="image"
    )
    def image_dither(command, channel, _, data, method="Floyd-Steinberg", **kwargs):
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            # if img.mode == "RGBA":
            #     pixel_data = img.load()
            #     width, height = img.size
            #     for y in range(height):
            #         for x in range(width):
            #             if pixel_data[x, y][3] == 0:
            #                 pixel_data[x, y] = (255, 255, 255, 255)

            # We don't need to apply F-S dithering ourselves, as pillow will do that for us
            if method != "Floyd-Steinberg":
                try:
                    inode.image = dither(inode.opaque_image, method)
                except NotImplementedError:
                    raise CommandSyntaxError("Method not recognized.")
            inode.image = inode.image.convert("1")
            update_image_node(inode)

        return "image", data

    @context.console_option(
        "distance",
        "d",
        type=float,
        help=_("Distance from color to be removed."),
        default=50.0,
    )
    @context.console_argument(
        "color", type=Color, help=_("Color to be removed"), default=Color("White")
    )
    @context.console_command(
        "remove",
        help=_("Remove color from image"),
        input_type="image",
        output_type="image",
    )
    def image_remove(command, channel, _, data, color, distance=1, **kwargs):
        if color is None:
            raise CommandSyntaxError(_("Must specify a color"))
        distance_sq = distance * distance

        def dist(px):
            r = color.red - px[0]
            g = color.green - px[1]
            b = color.blue - px[2]
            return r * r + g * g + b * b <= distance_sq

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            new_data = img.load()
            width, height = img.size
            for y in range(height):
                for x in range(width):
                    pixel = new_data[x, y]
                    if dist(pixel):
                        new_data[x, y] = (255, 255, 255, 0)
                        continue
            inode.image = img
            update_image_node(inode)

        return "image", data

    @context.console_argument("color", type=Color, help=_("Color to be added"))
    @context.console_command("add", help="", input_type="image", output_type="image")
    def image_add(command, channel, _, data, color, **kwargs):
        if color is None:
            channel(_("Must specify a color, to add."))
            return
        pix = (color.red, color.green, color.blue, color.alpha)
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            new_data = img.load()
            width, height = img.size
            for y in range(height):
                for x in range(width):
                    pixel = new_data[x, y]
                    if pixel[3] == 0:
                        new_data[x, y] = pix
                        continue
            inode.image = img
            update_image_node(inode)

        return "image", data

    @context.console_command(
        "dewhite", help="", input_type="image", output_type="image"
    )
    def image_dewhite(channel, _, data, **kwargs):
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode not in ("1", "L"):
                channel(_("Requires 1-bit or grayscale image."))
                return "image", data
            from PIL import Image

            black = Image.new("L", img.size, color="black")
            img = img.point(lambda e: 255 - e)
            black.putalpha(img)
            inode.image = black
            update_image_node(inode)

        return "image", data

    @context.console_command("rgba", help="", input_type="image", output_type="image")
    def image_rgba(command, channel, _, data, **kwargs):
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            inode.image = img
            update_image_node(inode)

        return "image", data

    @context.console_argument("left", help="left side of crop", type=int)
    @context.console_argument("upper", help="upper side of crop", type=int)
    @context.console_argument("right", help="right side of crop", type=int)
    @context.console_argument("lower", help="lower side of crop", type=int)
    @context.console_command(
        "crop", help=_("Crop image"), input_type="image", output_type="image"
    )
    def image_crop(command, channel, _, data, left, upper, right, lower, **kwargs):
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            try:
                if left >= right:
                    raise CommandSyntaxError(
                        _("Right margin is to the left of the left margin.")
                    )
                if upper >= lower:
                    raise CommandSyntaxError(
                        _("Lower margin is higher than the upper margin.")
                    )
                inode.image = img.crop((left, upper, right, lower))
                update_image_node(inode)

            except (KeyError, ValueError):
                raise CommandSyntaxError
        return "image", data

    @context.console_argument(
        "factor", type=float, help=_("contrast factor"), default=10.0
    )
    @context.console_command(
        "contrast",
        help=_("increase image contrast"),
        input_type="image",
        output_type="image",
    )
    def image_contrast(command, channel, _, data, factor, **kwargs):
        from PIL import ImageEnhance

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            try:
                img = inode.image
                enhancer = ImageEnhance.Contrast(img)
                inode.image = enhancer.enhance(factor)
                update_image_node(inode)

                channel(_("Image Contrast Factor: {factor}").format(factor=factor))
            except (IndexError, ValueError):
                channel(_("image contrast <factor>"))
        return "image", data

    @context.console_argument(
        "factor", type=float, help=_("contrast factor"), default=2.5
    )
    @context.console_command(
        "brightness", help=_("brighten image"), input_type="image", output_type="image"
    )
    def image_brightness(command, channel, _, data, factor, args=tuple(), **kwargs):
        from PIL import ImageEnhance

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            try:
                factor = float(args[1])
                img = inode.image
                enhancer = ImageEnhance.Brightness(img)
                inode.image = enhancer.enhance(factor)
                update_image_node(inode)

                channel(_("Image Brightness Factor: {factor}").format(factor=factor))
            except (IndexError, ValueError):
                channel(_("image brightness <factor>"))
        return "image", data

    @context.console_argument(
        "factor", type=float, help=_("color factor"), default=10.0
    )
    @context.console_command(
        "color", help=_("color enhance"), input_type="image", output_type="image"
    )
    def image_color(command, channel, _, data, factor, **kwargs):
        from PIL import ImageEnhance

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            try:
                img = inode.image
                enhancer = ImageEnhance.Color(img)
                inode.image = enhancer.enhance(factor)
                update_image_node(inode)

                channel(_("Image Color Factor: {factor}").format(factor=factor))
            except (IndexError, ValueError):
                channel(_("image color <factor>"))
        return "image", data

    @context.console_argument(
        "factor", type=float, help=_("sharpness factor"), default=10.0
    )
    @context.console_command(
        "sharpness", help=_("shapen image"), input_type="image", output_type="image"
    )
    def image_sharpness(command, channel, _, data, factor, **kwargs):
        from PIL import ImageEnhance

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            try:
                img = inode.image
                enhancer = ImageEnhance.Sharpness(img)
                inode.image = enhancer.enhance(factor)
                update_image_node(inode)

                channel(_("Image Sharpness Factor: {factor}").format(factor=factor))
            except (IndexError, ValueError):
                channel(_("image sharpness <factor>"))
        return "image", data

    @context.console_command(
        "blur", help=_("blur image"), input_type="image", output_type="image"
    )
    def image_blur(command, channel, _, data, **kwargs):
        from PIL import ImageFilter

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            inode.image = img.filter(filter=ImageFilter.BLUR)
            update_image_node(inode)

            channel(_("Image Blurred."))
        return "image", data

    @context.console_command(
        "sharpen", help=_("sharpen image"), input_type="image", output_type="image"
    )
    def image_sharpen(command, channel, _, data, **kwargs):
        from PIL import ImageFilter

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            inode.image = img.filter(filter=ImageFilter.SHARPEN)
            update_image_node(inode)

            channel(_("Image Sharpened."))
        return "image", data

    @context.console_command(
        "edge_enhance", help=_("enhance edges"), input_type="image", output_type="image"
    )
    def image_edge_enhance(command, channel, _, data, **kwargs):
        from PIL import ImageFilter

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            inode.image = img.filter(filter=ImageFilter.EDGE_ENHANCE)
            update_image_node(inode)

            channel(_("Image Edges Enhanced."))
        return "image", data

    @context.console_command(
        "find_edges", help=_("find edges"), input_type="image", output_type="image"
    )
    def image_find_edges(command, channel, _, data, **kwargs):
        from PIL import ImageFilter

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            inode.image = img.filter(filter=ImageFilter.FIND_EDGES)
            update_image_node(inode)

            channel(_("Image Edges Found."))
        return "image", data

    @context.console_command(
        "emboss", help=_("emboss image"), input_type="image", output_type="image"
    )
    def image_emboss(command, channel, _, data, **kwargs):
        from PIL import ImageFilter

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            inode.image = img.filter(filter=ImageFilter.EMBOSS)
            update_image_node(inode)

            channel(_("Image Embossed."))
        return "image", data

    @context.console_command(
        "smooth", help=_("smooth image"), input_type="image", output_type="image"
    )
    def image_smooth(command, channel, _, data, **kwargs):
        from PIL import ImageFilter

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            inode.image = img.filter(filter=ImageFilter.SMOOTH)
            update_image_node(inode)

            channel(_("Image Smoothed."))
        return "image", data

    @context.console_command(
        "contour", help=_("contour image"), input_type="image", output_type="image"
    )
    def image_contour(command, channel, _, data, **kwargs):
        from PIL import ImageFilter

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            inode.image = img.filter(filter=ImageFilter.CONTOUR)
            update_image_node(inode)

            channel(_("Image Contoured."))
        return "image", data

    @context.console_command(
        "detail", help=_("detail image"), input_type="image", output_type="image"
    )
    def image_detail(command, channel, _, data, **kwargs):
        from PIL import ImageFilter

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            inode.image = img.filter(filter=ImageFilter.DETAIL)
            update_image_node(inode)

            channel(_("Image Detailed."))
        return "image", data

    @context.console_argument(
        "colors", type=int, help=_("colors to quantize into"), default=10
    )
    @context.console_command(
        "quantize",
        help=_("image quantize <colors>"),
        input_type="image",
        output_type="image",
    )
    def image_quantize(command, channel, _, data, colors, **kwargs):
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            try:
                img = inode.image
                inode.image = img.quantize(colors=colors)
                update_image_node(inode)

                channel(_("Image Quantized to {count} colors.").format(count=colors))
            except (IndexError, ValueError):
                pass
        return "image", data

    @context.console_argument(
        "threshold", type=float, help=_("threshold for solarize"), default=250.0
    )
    @context.console_command(
        "solarize", help="", input_type="image", output_type="image"
    )
    def image_solarize(command, channel, _, data, threshold, **kwargs):
        from PIL import ImageOps

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            try:
                img = inode.opaque_image.convert("RGB")
                inode.image = ImageOps.solarize(img, threshold=threshold)
                update_image_node(inode)

                channel(
                    _("Image Solarized at {threshold} gray.").format(
                        threshold=threshold
                    )
                )
            except (IndexError, ValueError):
                channel(_("image solarize <threshold>"))
        return "image", data

    @context.console_command(
        "invert", help=_("invert the image"), input_type="image", output_type="image"
    )
    def image_invert(command, channel, _, data, **kwargs):
        from PIL import Image, ImageOps

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.opaque_image
            original_mode = inode.image.mode
            if img.mode == "RGBA":
                r, g, b, a = img.split()
                background = Image.new("RGB", img.size, "white")
                background.paste(img, mask=a)
                img = background
            elif img.mode in ("P", "1"):
                img = img.convert("RGB")
            try:
                inode.image = ImageOps.invert(img)
                if original_mode == "1":
                    inode.image = inode.image.convert("1")
                update_image_node(inode)

                channel(_("Image Inverted."))
            except OSError:
                channel(
                    _("Image type cannot be converted. {mode}").format(mode=img.mode)
                )
        context.signal("element_property_update", data)
        return "image", data

    @context.console_command(
        "flip", help=_("flip image"), input_type="image", output_type="image"
    )
    def image_flip(command, channel, _, data, **kwargs):
        from PIL import ImageOps

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            inode.image = ImageOps.flip(img)
            update_image_node(inode)

            channel(_("Image Flipped."))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_command(
        "mirror", help=_("mirror image"), input_type="image", output_type="image"
    )
    def image_mirror(command, channel, _, data, **kwargs):
        from PIL import ImageOps

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            inode.image = ImageOps.mirror(img)
            update_image_node(inode)

            channel(_("Image Mirrored."))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_command(
        "ccw", help=_("rotate image ccw"), input_type="image", output_type="image"
    )
    def image_ccw(command, channel, _, data, **kwargs):
        from PIL import Image

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            inode.image = img.transpose(Image.ROTATE_90)
            update_image_node(inode)

            channel(_("Rotated image counterclockwise."))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_command(
        "cw", help=_("rotate image cw"), input_type="image", output_type="image"
    )
    def image_cw(command, channel, _, data, **kwargs):
        from PIL import Image

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            inode.image = img.transpose(Image.ROTATE_270)
            update_image_node(inode)
            channel(_("Rotated image clockwise."))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_argument(
        "cutoff", type=float, help=_("cutoff limit for autocontrast"), default=128.0
    )
    @context.console_command(
        "autocontrast",
        help=_("autocontrast image"),
        input_type="image",
        output_type="image",
    )
    def image_autocontrast(command, channel, _, data, cutoff, **kwargs):
        from PIL import ImageOps

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            try:
                img = inode.opaque_image  # .convert("RGB")
                inode.image = ImageOps.autocontrast(img, cutoff=cutoff)
                update_image_node(inode)
                channel(_("Image Auto-Contrasted."))
            except (IndexError, ValueError):
                channel(_("image autocontrast <cutoff-percent>"))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_option(
        "method",
        "m",
        type=str,
        help=_("Method of grayscale conversion: red, green, blue, alpha"),
    )
    @context.console_command(
        ("grayscale", "greyscale"),
        help=_("convert image to grayscale"),
        input_type="image",
        output_type="image",
    )
    def image_grayscale(command, channel, _, data, method=None, **kwargs):
        from PIL import ImageOps

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if method is not None:
                if method == "red":
                    if inode.image.mode not in ("RGB", "RGBA"):
                        inode.image = inode.image.convert("RGBA")
                    inode.image = inode.image.getchannel("R")
                elif method == "green":
                    if inode.image.mode not in ("RGB", "RGBA"):
                        inode.image = inode.image.convert("RGBA")
                    inode.image = inode.image.getchannel("G")
                elif method == "blue":
                    if inode.image.mode not in ("RGB", "RGBA"):
                        inode.image = inode.image.convert("RGBA")
                    inode.image = inode.image.getchannel("B")
                elif method == "alpha":
                    if inode.image.mode not in ("LA", "RGBA"):
                        inode.image = inode.image.convert("RGBA")
                    inode.image = inode.image.getchannel("A")
            else:
                inode.image = ImageOps.grayscale(img)
            update_image_node(inode)
            channel(_("Image Grayscale."))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_command(
        "equalize", help=_("equalize image"), input_type="image", output_type="image"
    )
    def image_equalize(command, channel, _, data, **kwargs):
        from PIL import ImageOps

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.opaque_image.convert("RGB")
            inode.image = ImageOps.equalize(img)
            update_image_node(inode)
            channel(_("Image Equalized."))
        context.signal("element_property_update", data)
        return "image", data

    @context.console_argument(
        "x1",
        type=float,
        help=_("X position of image cutline"),
    )
    @context.console_argument(
        "y1",
        type=float,
        help=_("Y position of image cutline"),
    )
    @context.console_argument(
        "x2",
        type=float,
        help=_("X position of image cutline"),
    )
    @context.console_argument(
        "y2",
        type=float,
        help=_("Y position of image cutline"),
    )
    @context.console_command(
        "linecut",
        help=_("Cuts and image with a line"),
        input_type="image",
        output_type="image",
        hidden=True,
    )
    def image_linecut(command, channel, _, data, x1, y1, x2, y2, **kwargs):
        data_out = list()
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            b = inode.bounds

            from meerk40t.core.node.elem_path import PathNode
            from meerk40t.core.node.elem_rect import RectNode
            from meerk40t.extra.imageactions import create_image, mask_image

            rectnode = RectNode(
                x=b[0],
                y=b[1],
                width=b[2] - b[0],
                height=b[3] - b[1],
                stroke=None,
                fill=None,
            )
            bounds_rect = Geomstr.rect(b[0], b[1], b[2] - b[0], b[3] - b[1])
            line = Geomstr.lines(complex(x1, y1), complex(x2, y2))
            geoms = bounds_rect.divide(line)
            parent = inode.parent

            make_raster = context.elements.lookup("render-op/make_raster")

            elemimage, elemmatrix = create_image(
                make_raster, [inode], b, inode.dpi, keep_ratio=True
            )

            for g in geoms:
                masknode = PathNode(geometry=g, stroke=None, fill=Color("black"))
                # Make sure they have the right size by adding a dummy node to it...

                maskimage, maskmatrix = create_image(
                    make_raster, (masknode, rectnode), b, inode.dpi, keep_ratio=True
                )
                if maskimage is None or elemimage is None:
                    channel(_("Intermediary images were none"))
                    continue

                out = mask_image(
                    elemimage, maskimage, elemmatrix, inode.dpi, dx=b[0], dy=b[1]
                )
                for imnode in out:
                    parent.add_node(imnode)
                data_out.extend(out)

        context.signal("element_property_update", data_out)
        return "image", data_out

    @context.console_argument(
        "x",
        type=int,
        help=_("X position at which to slice the image"),
    )
    @context.console_command(
        "slice",
        help=_("Slice image cutting it vertically into two images."),
        input_type="image",
        output_type="image",
    )
    def image_slice(command, channel, _, data, x, **kwargs):
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            image_left = img.crop((0, 0, x, inode.image.height))
            image_right = img.crop((x, 0, inode.image.width, inode.image.height))

            parent = inode.parent

            inode.remove_node()
            elements = context.elements

            node1 = parent.add(
                type="elem image", matrix=Matrix(inode.matrix), image=image_left
            )
            node2 = parent.add(
                type="elem image", matrix=Matrix(inode.matrix), image=image_right
            )
            node2.matrix.pre_translate(x)
            elements.classify([node1, node2])
            channel(_("Image sliced at position {position}").format(position=x))
            return "image", [node1, node2]

        context.signal("element_property_update", data)
        return "image", data

    @context.console_argument(
        "y",
        type=int,
        help=_("Y position at which to slash the image"),
    )
    @context.console_command(
        "slash",
        help=_("Slash image cutting it horizontally into two images"),
        input_type="image",
        output_type="image",
    )
    def image_slash(command, channel, _, data, y, **kwargs):
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            image_top = img.crop((0, 0, inode.image.width, y))
            image_bottom = img.crop((0, y, inode.image.width, inode.image.height))

            parent = inode.parent

            inode.remove_node()
            elements = context.elements

            node1 = parent.add(
                type="elem image", matrix=Matrix(inode.matrix), image=image_top
            )
            node2 = parent.add(
                type="elem image", matrix=Matrix(inode.matrix), image=image_bottom
            )
            node2.matrix.pre_translate(0, y)

            elements.classify([node1, node2])
            channel(_("Image slashed at position {position}").format(position=y))
            return "image", [node1, node2]

        return "image", data

    @context.console_option(
        "remain",
        "r",
        help="Do not blank the popped region from the remainder image",
        action="store_true",
        type=bool,
    )
    @context.console_argument("left", help="left side of crop", type=int)
    @context.console_argument("upper", help="upper side of crop", type=int)
    @context.console_argument("right", help="right side of crop", type=int)
    @context.console_argument("lower", help="lower side of crop", type=int)
    @context.console_command(
        "pop",
        help=_("Pop pixels for more efficient rastering"),
        input_type="image",
        output_type="image",
    )
    def image_pop(
        command, channel, _, data, left, upper, right, lower, remain=False, **kwargs
    ):
        from PIL import Image

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            img = inode.image
            if img.mode == "P":
                img = img.convert("RGBA")
            if left >= right:
                raise CommandSyntaxError(
                    _("Right margin is to the left of the left margin.")
                )
            if upper >= lower:
                raise CommandSyntaxError(
                    _("Lower margin is higher than the upper margin.")
                )
            image_popped = img.crop((left, upper, right, lower))
            image_remain = img.copy()

            if not remain:
                image_blank = Image.new("L", image_popped.size, 255)
                image_remain.paste(image_blank, (left, upper))

            inode_pop = copy(inode)
            inode_pop.image = image_popped

            inode_pop.transform.pre_translate(left, upper)

            inode_remain = copy(inode)
            inode_remain.image = image_remain

            inode.remove_node()

            elements = context.elements
            node1 = elements.elem_branch.add(image=inode_remain, type="elem image")
            node2 = elements.elem_branch.add(image=inode_pop, type="elem image")
            elements.classify([node1, node2])

        return "image", data

    @context.console_option(
        "processed",
        "p",
        help=_("Save the processed image to disk"),
        action="store_true",
        type=bool,
    )
    @context.console_argument(
        "filename", type=str, help=_("filename"), default="output.png"
    )
    @context.console_command(
        "save", help=_("save image to disk"), input_type="image", output_type="image"
    )
    def image_save(command, channel, _, data, filename, processed=None, **kwargs):
        if processed is None:
            processed = False
        for inode in data:
            try:
                if processed and inode._processed_image is not None:
                    img = inode._processed_image
                else:
                    img = inode.image
                img.save(filename)
                channel(_("Saved: {filename}").format(filename=filename))
            except IndexError:
                channel(_("No file given."))
            except OSError:
                channel(_("File could not be written / created."))
            except ValueError:
                channel(_("Could not determine expected format."))
        return "image", data

    @context.console_command(
        "flatrotary", help=_("apply flatrotary bilinear mesh"), input_type="image"
    )
    def image_flatrotary(command, channel, _, data, args=tuple(), **kwargs):
        """
        Flat rotary stretches an image according to the rotary settings. Providing a series of points it applies a
        bi-linear mesh to stretch the image across the x-axis creating an image that can be interpreted as flat on a
        curved surface. Values are between 0 and 1. The number of values given mark equidistant points however if the
        values given are not themselves equidistant the resulting image is stretched accordingly.

        e.g. flatrotary 0 .2 .7 1
        """
        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            points = len(args) - 1
            im = inode.image
            w, h = im.size
            from PIL import Image

            def t(i, width):
                return int(i * width / (points - 1))

            def x(i, width):
                return int(width * float(args[i + 1]))

            boxes = list((t(i, w), 0, t(i + 1, w), h) for i in range(points - 1))
            quads = list(
                (x(i, w), 0, x(i, w), h, x(i + 1, w), h, x(i + 1, w), 0)
                for i in range(points - 1)
            )
            mesh = list(zip(boxes, quads))
            inode.image = im.transform(im.size, Image.MESH, mesh, Image.BILINEAR)
            update_image_node(inode)
        return "image", data

    @context.console_option(
        "scale", "s", type=int, help=_("process scaling"), default=1
    )
    @context.console_argument(
        "oversample", type=int, help=_("pixel oversample amount"), default=2
    )
    @context.console_argument(
        "sample", type=int, help=_("pixel sample size"), default=10
    )
    @context.console_argument(
        "angle", type=Angle, help=_("half-tone angle"), default="22deg"
    )
    @context.console_command(
        "halftone",
        help=_("halftone the provided image"),
        input_type="image",
        output_type="image",
    )
    def image_halftone(
        command,
        channel,
        _,
        data,
        oversample,
        sample=10,
        scale=1,
        angle=None,
        **kwargs,
    ):
        """
        Returns halftone image for image.

        The maximum output dot diameter is given by sample * scale (which is also the number of possible dot sizes).
        So sample=1 will preserve the original image resolution, but scale must be >1 to allow variation in dot size.
        """
        if angle is None:
            raise CommandSyntaxError
        from PIL import Image, ImageDraw, ImageStat

        angle_degrees = angle.degrees

        for inode in data:
            if inode.lock:
                channel(
                    _("Can't modify a locked image: {name}").format(name=str(inode))
                )
                continue
            im = inode.image
            img = inode.opaque_image
            image = img.convert("L")
            image = image.rotate(angle_degrees, expand=1)
            size = image.size[0] * scale, image.size[1] * scale
            half_tone = Image.new("L", size)
            draw = ImageDraw.Draw(half_tone)
            for x in range(0, image.size[0], sample):
                for y in range(0, image.size[1], sample):
                    box = image.crop(
                        (
                            x - oversample,
                            y - oversample,
                            x + sample + oversample,
                            y + sample + oversample,
                        )
                    )
                    stat = ImageStat.Stat(box)
                    diameter = (stat.mean[0] / 255) ** 0.5
                    edge = 0.5 * (1 - diameter)
                    x_pos, y_pos = (x + edge) * scale, (y + edge) * scale
                    box_edge = sample * diameter * scale
                    draw.ellipse(
                        (x_pos, y_pos, x_pos + box_edge, y_pos + box_edge), fill=255
                    )
            half_tone = half_tone.rotate(-angle, expand=1)
            width_half, height_half = half_tone.size
            xx = (width_half - im.size[0] * scale) / 2
            yy = (height_half - im.size[1] * scale) / 2
            half_tone = half_tone.crop(
                (xx, yy, xx + im.size[0] * scale, yy + im.size[1] * scale)
            )
            inode.image = half_tone
            update_image_node(inode)
        return "image", data

    @context.console_option("minimal", "m", type=int, help=_("minimal area"), default=2)
    @context.console_option(
        "outer",
        "o",
        type=bool,
        help=_("Ignore outer areas"),
        action="store_true",
    )
    @context.console_option(
        "simplified",
        "s",
        type=bool,
        help=_("Display simplified outline"),
        action="store_true",
    )
    @context.console_option(
        "line",
        "l",
        type=bool,
        help=_("Show split line candidates"),
        action="store_true",
    )
    @context.console_option(
        "breakdown",
        "b",
        type=bool,
        help=_("Break the image apart into slices"),
        action="store_true",
    )
    @context.console_option(
        "whiten",
        "w",
        type=bool,
        help=_("Break the image apart but whiten non-used areas"),
        action="store_true",
    )
    @context.console_command(
        "innerwhite",
        help=_("identify inner white areas in image"),
        input_type="image",
        output_type="image",
    )
    def image_white(
        command,
        channel,
        _,
        minimal=None,
        outer=False,
        simplified=False,
        line=False,
        breakdown=False,
        whiten=False,
        data=None,
        post=None,
        **kwargs,
    ):
        try:
            import cv2
            import numpy as np
        except ImportError:
            channel("Either cv2 or numpy weren't installed")
            return
        # from PIL import Image
        if data is None:
            channel(_("No elements selected"))

        if minimal is None:
            minimal = 2
        if minimal <= 0 or minimal > 100:
            minimal = 2

        data_out = list()

        show_contour = not simplified
        show_simplified = simplified
        if breakdown and whiten:
            channel("You can't use --breakdown and --whiten at the same time")
            return
        if breakdown or whiten:
            line = False
            show_simplified = False
            show_contour = False

        # channel (f"Options: breakdown={breakdown}, contour={show_contour}, simplified contour={show_simplified}, lines={line}")
        for inode in data:
            # node_image = inode.active_image
            node_image = inode.image
            width, height = node_image.size
            if width == 0 or height == 0:
                continue
            if not hasattr(inode, "bounds"):
                continue
            bb = inode.bounds
            ox = bb[0]
            oy = bb[1]
            coord_width = bb[2] - bb[0]
            coord_height = bb[3] - bb[1]

            def getpoint(ix, iy):
                # Translate image to scene coordinates
                return (
                    ox + ix / width * coord_width,
                    oy + iy / height * coord_height,
                )

            gray = np.array(node_image.convert("L"))
            # Threshold the image
            _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY)

            # Find contours
            contours, hierarchy = cv2.findContours(
                thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            linecandidates = list()

            minarea = int(minimal / 100.0 * width * height)
            # Filter contours based on area, rectangle of at least x%

            large_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > minarea]
            if len(large_contours) == 0:
                channel(f"Could not identify any relevant white areas in the image '{inode.create_label('{desc}')}'")
                continue

            # Create some rectangles around the white areas
            for contour in large_contours:
                # Each individual contour is a Numpy array of (x, y) coordinates of boundary points of the object
                x, y, w, h = cv2.boundingRect(contour)
                # rx, ry = getpoint(x, y)
                rw, rh = getpoint(w, h)
                rw -= ox
                rh -= oy
                if outer:
                    # leftmost
                    extreme = tuple(contour[contour[:, :, 0].argmin()][0])
                    if extreme[0] == 0:
                        # print ("Left edge")
                        continue
                    # rightmost
                    extreme = tuple(contour[contour[:, :, 0].argmax()][0])
                    if extreme[0] >= width - 1:
                        # print ("Right edge")
                        continue
                    # topmost
                    extreme = tuple(contour[contour[:, :, 1].argmin()][0])
                    if extreme[1] == 0:
                        # print ("Top edge")
                        continue
                    # bottommost
                    extreme = tuple(contour[contour[:, :, 1].argmax()][0])
                    if extreme[1] >= height - 1:
                        # print ("Bottom edge")
                        continue

                linecandidates.append((x, w))
                area = cv2.contourArea(contour)
                rect_area = w * h
                extent = float(area) / rect_area
                # print (f"x={x}, y={y}, w={w}, h={h}, extent={extent*100:.1f}%")
                label = f"Contour - Area={100 * area / (width * height):.1f}%, Extent={extent*100:.1f}%"
                # if show_rect:
                #     node = context.elements.elem_branch.add(
                #         x=rx,
                #         y=ry,
                #         width=rw,
                #         height=rh,
                #         stroke=Color("red"),
                #         label=label,
                #         type="elem rect",
                #     )
                #     data_out.append(node)
                if show_contour:
                    geom = Geomstr()
                    notfirst = False
                    for c in contour:
                        for e in c:
                            rx, ry = getpoint(e[0], e[1])
                            if notfirst:
                                geom.line(complex(lx, ly), complex(rx, ry))
                            notfirst = True
                            lx = rx
                            ly = ry
                    geom.close()
                    node = context.elements.elem_branch.add(
                        geometry=geom,
                        stroke=Color("blue"),
                        fill=Color("yellow"),
                        label=label,
                        type="elem path",
                    )
                    data_out.append(node)
                if show_simplified:
                    # Set the epsilon value (adjust as needed)
                    epsilon = 0.01 * cv2.arcLength(contour, True)

                    # Compute the approximate contour points
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    geom = Geomstr()
                    notfirst = False
                    for c in approx:
                        for e in c:
                            rx, ry = getpoint(e[0], e[1])
                            if notfirst:
                                geom.line(complex(lx, ly), complex(rx, ry))
                            notfirst = True
                            lx = rx
                            ly = ry
                    geom.close()
                    node = context.elements.elem_branch.add(
                        geometry=geom,
                        stroke=Color("green"),
                        label=label,
                        type="elem path",
                    )
                    data_out.append(node)

                # if show_extreme:
                #     # leftmost
                #     extreme = tuple(contour[contour[:, :, 0].argmin()][0])
                #     lmx, lmy = getpoint(extreme[0], extreme[1])
                #     # rightmost
                #     extreme = tuple(contour[contour[:, :, 0].argmax()][0])
                #     rmx, rmy = getpoint(extreme[0], extreme[1])
                #     # topmost
                #     extreme = tuple(contour[contour[:, :, 1].argmin()][0])
                #     tmx, tmy = getpoint(extreme[0], extreme[1])
                #     # bottommost
                #     extreme = tuple(contour[contour[:, :, 1].argmax()][0])
                #     bmx, bmy = getpoint(extreme[0], extreme[1])
                #     geom = Geomstr()
                #     geom.line(lmx + 1j * lmy, tmx + 1j * tmy)
                #     geom.line(tmx + 1j * tmy, rmx + 1j * rmy)
                #     geom.line(rmx + 1j * rmy, bmx + 1j * bmy)
                #     geom.line(bmx + 1j * bmy, lmx + 1j * lmy)
                #     node = context.elements.elem_branch.add(
                #         geometry=geom,
                #         stroke=Color("green"),
                #         label=label,
                #         type="elem path",
                #     )
                #     data_out.append(node)
            linecandidates.sort(key=lambda e: e[0])
            if line or breakdown or whiten:
                for idx1, c in enumerate(linecandidates):
                    if c[0] < 0:
                        continue
                    # cx = c[0] + c[1] / 2
                    for idx2, d in enumerate(linecandidates):
                        if idx1 == idx2 or d[0] < 0:
                            continue
                        # Does c line inside d? if yes then we don't need d
                        if d[0] <= c[0] and d[0] + d[1] >= c[0] + c[1]:
                            linecandidates[idx2] = (-1, -1)
            if line:
                for c in linecandidates:
                    if c[0] < 0:
                        continue
                    sx, sy = getpoint(c[0] + c[1] / 2, 0)
                    ex, ey = getpoint(c[0] + c[1] / 2, height)
                    node = context.elements.elem_branch.add(
                        x1=sx,
                        y1=sy,
                        x2=ex,
                        y2=ey,
                        stroke=Color("red"),
                        label="Splitline",
                        type="elem line",
                    )
                    data_out.append(node)
            white_paste = (255, 255, 255)
            if breakdown or whiten:
                anyslices = 0
                right_image = node_image.copy()
                dx = 0
                for c in linecandidates:
                    if c[0] < 0:
                        continue
                    rdx, rdy = getpoint(dx, 0)
                    rdx -= ox
                    rwidth, rheight = right_image.size
                    anyslices += 1
                    if breakdown:
                        x = int(c[0] + c[1] / 2 - dx)
                        left_image = right_image.crop((0, 0, x, rheight))
                        dx = x + 1
                        right_image = right_image.crop((dx, 0, rwidth, rheight))
                    elif whiten:
                        x = int(c[0] + c[1] / 2)
                        left_image = right_image.copy()
                        # print(f"Break position: {x}")
                        if dx > 0:
                            # print(f"Erasing left: 0:{dx - 1}")
                            left_image.paste(white_paste, (0, 0, dx - 1, rheight))
                        dx = x + 1
                        left_image.paste(white_paste, (dx, 0, rwidth, rheight))
                        # print(f"Erasing right: {dx}:{rwidth}")
                    newnode = copy(inode)
                    newnode.label = (
                        f"[{anyslices}]{'' if inode.label is None else inode.label}"
                    )
                    # newnode.dither = False
                    # newnode.operations.clear()
                    # newnode.prevent_crop = True
                    newnode.image = left_image
                    if breakdown and rdx != 0:
                        newnode.matrix.post_translate_x(rdx)
                    if whiten:
                        newnode.prevent_crop = True

                    newnode.altered()
                    newnode._processed_image = None

                    context.elements.elem_branch.add_node(newnode)
                    data_out.append(newnode)
                if anyslices > 0:
                    rdx, rdy = getpoint(dx, 0)
                    rdx -= ox
                    anyslices += 1
                    newnode = copy(inode)
                    newnode.label = (
                        f"[{anyslices}]{'' if inode.label is None else inode.label}"
                    )
                    # newnode.dither = False
                    # newnode.operations.clear()
                    # newnode.prevent_crop = True
                    if whiten:
                        if dx > 0:
                            # print(f"Last, erasing left: 0:{dx - 1}")
                            right_image.paste(white_paste, (0, 0, dx - 1, rheight))
                    newnode.image = right_image
                    if breakdown and rdx != 0:
                        newnode.matrix.post_translate_x(rdx)
                    if whiten:
                        newnode.prevent_crop = True
                    newnode.altered()
                    newnode._processed_image = None
                    context.elements.elem_branch.add_node(newnode)
                    data_out.append(newnode)

                    inode.remove_node()

        post.append(context.elements.post_classify(data_out))
        return "image", data_out


class RasterScripts:
    """
    This module serves as the raster scripting routine. It registers raster-scripts and
    processes the known items in known ways. This should be made accessible to the CLI.

    Please note: Lists of instructions and methods are not copyrightable. While the actual text
    itself of various descriptions of procedures can be copyrighted the actual methods and procedures
    cannot be copyrighted themselves. If particular procedures may qualify for or be registered for a
    trademark, the name will be changed to avoid infringing. No patented procedures (e.g. seam carving)
    will be permitted.

    I'm happy to take anybody's recipes for raster-preprocessing, while texts of scripts may be copyrighted
    the thing they do cannot be.
    """

    @staticmethod
    def raster_script_gold():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "dpi": 333}
        )
        ops.append(
            {
                "name": "grayscale",
                "enable": True,
                "invert": False,
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
                "lightness": 1.0,
            }
        )
        ops.append(
            {
                "name": "contrast",
                "enable": True,
                "contrast": 25,
                "brightness": 25,
            }
        )
        ops.append(
            {
                "name": "unsharp_mask",
                "enable": True,
                "percent": 500,
                "radius": 4,
                "threshold": 0,
            }
        )
        ops.append(
            {
                "name": "unsharp_mask",
                "enable": False,
                "percent": 150,
                "radius": 1,
                "threshold": 0,
            }
        )
        ops.append({"name": "dither", "enable": True, "type": "Floyd-Steinberg"})
        return ops

    @staticmethod
    def raster_script_stipo():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "dpi": 500}
        )
        ops.append(
            {
                "name": "grayscale",
                "enable": True,
                "invert": False,
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
                "lightness": 1.0,
            }
        )
        ops.append(
            {
                "name": "tone",
                "type": "spline",
                "enable": True,
                "values": [[0, 0], [100, 150], [255, 255]],
            }
        )
        ops.append({"name": "gamma", "enable": True, "factor": 3.5})
        ops.append(
            {
                "name": "unsharp_mask",
                "enable": True,
                "percent": 500,
                "radius": 20,
                "threshold": 6,
            }
        )
        ops.append({"name": "dither", "enable": True, "type": "Floyd-Steinberg"})
        return ops

    @staticmethod
    def raster_script_gravy():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "dpi": 333}
        )
        ops.append(
            {
                "name": "grayscale",
                "enable": True,
                "invert": False,
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
                "lightness": 1.0,
            }
        )
        ops.append({"name": "edge_enhance", "enable": False})
        ops.append({"name": "auto_contrast", "enable": True, "cutoff": 3})
        ops.append(
            {
                "name": "unsharp_mask",
                "enable": True,
                "percent": 500,
                "radius": 4,
                "threshold": 0,
            }
        )
        ops.append(
            {
                "name": "tone",
                "type": "line",
                "enable": True,
                "values": [
                    (2, 32),
                    (9, 50),
                    (30, 84),
                    (40, 99),
                    (76, 144),
                    (101, 170),
                    (126, 193),
                    (156, 214),
                    (181, 230),
                    (206, 246),
                    (256, 254),
                ],
            }
        )
        ops.append({"name": "dither", "enable": True, "type": "Floyd-Steinberg"})
        return ops

    @staticmethod
    def raster_script_xin():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "dpi": 500}
        )
        ops.append(
            {
                "name": "grayscale",
                "enable": True,
                "invert": False,
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
                "lightness": 1.0,
            }
        )
        ops.append(
            {
                "name": "tone",
                "type": "spline",
                "enable": True,
                "values": [[0, 0], [100, 125], [255, 255]],
            }
        )
        ops.append(
            {
                "name": "unsharp_mask",
                "enable": True,
                "percent": 100,
                "radius": 8,
                "threshold": 0,
            }
        )
        ops.append({"name": "dither", "enable": True, "type": "Floyd-Steinberg"})
        return ops

    @staticmethod
    def raster_script_newsy():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "dpi": 500}
        )
        ops.append(
            {
                "name": "grayscale",
                "enable": True,
                "invert": False,
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
                "lightness": 1.0,
            }
        )
        ops.append(
            {
                "name": "contrast",
                "enable": True,
                "contrast": 25,
                "brightness": 25,
            }
        )
        ops.append(
            {
                "name": "halftone",
                "enable": True,
                "black": True,
                "sample": 10,
                "angle": 22,
                "oversample": 2,
            }
        )
        ops.append({"name": "dither", "enable": True, "type": "Floyd-Steinberg"})
        return ops

    @staticmethod
    def raster_script_simple():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "dpi": 333}
        )
        ops.append(
            {
                "name": "grayscale",
                "enable": True,
                "invert": False,
                "red": 1.0,
                "green": 1.0,
                "blue": 1.0,
                "lightness": 1.0,
            }
        )
        ops.append({"name": "dither", "enable": True, "type": "Floyd-Steinberg"})
        return ops

    @staticmethod
    def halftone(image, sample=10, scale=3.0, angle=22.0, oversample=2, black=False):
        from PIL import Image, ImageDraw, ImageStat

        original_image = image
        image = image.convert("L")
        image = image.rotate(angle, expand=1)
        size = int(image.size[0] * scale), int(image.size[1] * scale)
        if black:
            half_tone = Image.new("L", size, color=255)
        else:
            half_tone = Image.new("L", size)
        draw = ImageDraw.Draw(half_tone)
        if sample == 0:
            sample = 1
        for x in range(0, image.size[0], sample):
            for y in range(0, image.size[1], sample):
                box = image.crop(
                    (
                        x - oversample,
                        y - oversample,
                        x + sample + oversample,
                        y + sample + oversample,
                    )
                )
                stat = ImageStat.Stat(box)
                if black:
                    diameter = ((255 - stat.mean[0]) / 255) ** 0.5
                else:
                    diameter = (stat.mean[0] / 255) ** 0.5
                edge = 0.5 * (1 - diameter)
                x_pos, y_pos = (x + edge) * scale, (y + edge) * scale
                box_edge = sample * diameter * scale
                if black:
                    draw.ellipse(
                        (x_pos, y_pos, x_pos + box_edge, y_pos + box_edge), fill=0
                    )
                else:
                    draw.ellipse(
                        (x_pos, y_pos, x_pos + box_edge, y_pos + box_edge), fill=255
                    )
        half_tone = half_tone.rotate(-angle, expand=1)
        width_half, height_half = half_tone.size
        xx = (width_half - original_image.size[0] * scale) / 2
        yy = (height_half - original_image.size[1] * scale) / 2
        half_tone = half_tone.crop(
            (
                xx,
                yy,
                xx + original_image.size[0] * scale,
                yy + original_image.size[1] * scale,
            )
        )
        half_tone = half_tone.resize(original_image.size)
        return half_tone

    @staticmethod
    def line(p):
        N = len(p) - 1
        try:
            m = [(p[i + 1][1] - p[i][1]) / (p[i + 1][0] - p[i][0]) for i in range(0, N)]
        except ZeroDivisionError:
            m = [1] * N
        # b = y - mx
        b = [p[i][1] - (m[i] * p[i][0]) for i in range(0, N)]
        r = list()
        for i in range(0, p[0][0]):
            r.append(0)
        for i in range(len(p) - 1):
            x0 = p[i][0]
            x1 = p[i + 1][0]
            range_list = [int(round((m[i] * x) + b[i])) for x in range(x0, x1)]
            r.extend(range_list)
        for i in range(p[-1][0], 256):
            r.append(255)
        r.append(round(int(p[-1][1])))
        return r

    @staticmethod
    def spline(p):
        """
        Spline interpreter.

        Returns all integer locations between different spline interpolation values
        @param p: points to be quad spline interpolated.
        @return: integer y values for given spline points.
        """
        try:
            N = len(p) - 1
            w = [(p[i + 1][0] - p[i][0]) for i in range(0, N)]
            h = [(p[i + 1][1] - p[i][1]) / w[i] for i in range(0, N)]
            ftt = (
                [0]
                + [3 * (h[i + 1] - h[i]) / (w[i + 1] + w[i]) for i in range(0, N - 1)]
                + [0]
            )
            A = [(ftt[i + 1] - ftt[i]) / (6 * w[i]) for i in range(0, N)]
            B = [ftt[i] / 2 for i in range(0, N)]
            C = [h[i] - w[i] * (ftt[i + 1] + 2 * ftt[i]) / 6 for i in range(0, N)]
            D = [p[i][1] for i in range(0, N)]
        except ZeroDivisionError:
            return list(range(256))
        r = list()
        for i in range(0, p[0][0]):
            r.append(0)
        for i in range(len(p) - 1):
            a = p[i][0]
            b = p[i + 1][0]
            r.extend(
                int(
                    round(
                        A[i] * (x - a) ** 3
                        + B[i] * (x - a) ** 2
                        + C[i] * (x - a)
                        + D[i]
                    )
                )
                for x in range(a, b)
            )
        for i in range(p[-1][0], 256):
            r.append(255)
        r.append(round(int(p[-1][1])))
        return r


class ImageLoader:
    @staticmethod
    def load_types():
        yield "Portable Network Graphics", ("png",), "image/png"
        yield "Bitmap Graphics", ("bmp",), "image/bmp"
        yield "EPS Format", ("eps",), "image/eps"
        yield "TIFF Format", ("tiff",), "image/tiff"
        yield "GIF Format", ("gif",), "image/gif"
        yield "Icon Format", ("ico",), "image/ico"
        yield "JPEG Format", ("jpg", "jpeg", "jpe"), "image/jpeg"
        yield "Webp Format", ("webp",), "image/webp"

    @staticmethod
    def load(context, elements_service, pathname, **kwargs):
        if pathname is None:
            return False
        try:
            from PIL import Image as PILImage
            from PIL.Image import DecompressionBombError
        except ImportError:
            return False
        try:
            image = PILImage.open(pathname)
            image.copy()  # Throws error for .eps without ghostscript
        except OSError:
            return False
        except DecompressionBombError as e:
            raise BadFileError("Image is larger than 178 megapixels.") from e
        except subprocess.CalledProcessError as e:
            raise BadFileError(
                "Cannot load an .eps file without GhostScript installed"
            ) from e
        try:
            from PIL import ImageOps

            image = ImageOps.exif_transpose(image)
        except ImportError:
            pass
        _dpi = DEFAULT_PPI
        matrix = Matrix(f"scale({UNITS_PER_PIXEL})")
        try:
            context.setting(bool, "image_dpi", True)
            if context.image_dpi:
                try:
                    dpi = image.info["dpi"]
                except KeyError:
                    dpi = None
                if (
                    isinstance(dpi, tuple)
                    and len(dpi) >= 2
                    and dpi[0] != 0
                    and dpi[1] != 0
                ):
                    matrix.post_scale(
                        DEFAULT_PPI / float(dpi[0]), DEFAULT_PPI / float(dpi[1])
                    )
                    _dpi = round((float(dpi[0]) + float(dpi[1])) / 2, 0)
        except (KeyError, IndexError):
            pass

        context.setting(bool, "create_image_group", True)
        element_branch = elements_service.get(type="branch elems")
        if context.create_image_group:
            file_node = element_branch.add(
                type="file", label=os.path.basename(pathname)
            )
            file_node.filepath = pathname
        else:
            file_node = element_branch
        n = file_node.add(
            image=image,
            matrix=matrix,
            # type="image raster",
            type="elem image",
            dpi=_dpi,
        )
        if context.create_image_group:
            file_node.focus()
        else:
            n.focus()
        elements_service.classify([n])
        return True
