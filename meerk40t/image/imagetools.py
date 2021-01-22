from os import path as ospath
from copy import copy
from math import ceil

from ..core.cutplanner import CutPlanner
from ..svgelements import SVGImage, Color, Length, Path, Matrix


def plugin(kernel, lifecycle=None):
    """
    ImageTools mostly provides the image functionality to the console. It should be loaded in the root context.
    This functionality will largely depend on PIL/Pillow for the image command subfunctions.
    """

    if lifecycle != "register":
        return

    kernel.register("raster_script/Gold", RasterScripts.raster_script_gold())
    kernel.register("raster_script/Stipo", RasterScripts.raster_script_stipo())
    kernel.register("raster_script/Gravy", RasterScripts.raster_script_gravy())
    kernel.register("raster_script/Xin", RasterScripts.raster_script_xin())
    kernel.register("raster_script/Newsy", RasterScripts.raster_script_newsy())
    kernel.register("raster_script/Simple", RasterScripts.raster_script_simple())
    kernel.register("load/ImageLoader", ImageLoader)
    context = kernel.get_context('/')

    @context.console_command("image", help="image <operation>")
    def image(command, channel, _, args=tuple(), **kwargs):
        elements = context.elements
        if len(args) == 0:
            channel(_("----------"))
            channel(_("Images:"))
            i = 0
            for element in elements.elems():
                if not isinstance(element, SVGImage):
                    continue
                name = str(element)
                if len(name) > 50:
                    name = name[:50] + "..."
                yield channel(
                    "%d: (%d, %d) %s, %s"
                    % (
                        i,
                        element.image_width,
                        element.image_height,
                        element.image.mode,
                        name,
                    )
                )
                i += 1
            channel(_("----------"))
            return
        if not elements.has_emphasis():
            channel(_("No selected images."))
            return
        elif args[0] == "path":
            for element in list(elements.elems(emphasized=True)):
                bounds = element.bbox()
                p = Path()
                p.move(
                    (bounds[0], bounds[1]),
                    (bounds[0], bounds[3]),
                    (bounds[2], bounds[3]),
                    (bounds[2], bounds[1]),
                )
                p.closed()
                elements.add_element(p)
            return
        elif args[0] == "wizard":
            if len(args) == 1:
                try:
                    for script_name in context.match("raster_script", True):
                        channel(_("Raster Script: %s") % script_name)
                except KeyError:
                    channel(_("No Raster Scripts Found."))
                return
            try:
                script = context.registered["raster_script/%s" % args[1]]
            except KeyError:
                channel(_("Raster Script %s is not registered.") % args[1])
                return

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    (
                        element.image,
                        element.transform,
                        step,
                    ) = RasterScripts.wizard_image(element, script)
                    if step is not None:
                        element.values["raster_step"] = step
                    element.image_width, element.image_height = element.image.size
                    element.lock = True
                    element.altered()
            return
        elif args[0] == "unlock":
            channel(_("Unlocking Elements..."))
            for element in elements.elems(emphasized=True):
                try:
                    if element.lock:
                        channel("Unlocked: %s" % str(element))
                        element.lock = False
                    else:
                        channel(_("Element was not locked: %s") % str(element))
                except AttributeError:
                    channel(_("Element was not locked: %s") % str(element))
            return
        elif args[0] == "threshold":
            try:
                threshold_min = float(args[1])
                threshold_max = float(args[2])
            except (ValueError, IndexError):
                channel(_("Threshold values improper."))
                return
            divide = (threshold_max - threshold_min) / 255.0
            for element in elements.elems(emphasized=True):
                if not isinstance(element, SVGImage):
                    continue
                image_element = copy(element)
                image_element.image = image_element.image.copy()
                try:
                    from .cutplanner import OperationPreprocessor
                except ImportError:
                    channel("No Render Engine Installed.")
                    return
                if OperationPreprocessor.needs_actualization(image_element):
                    OperationPreprocessor.make_actual(image_element)
                img = image_element.image
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
                image_element.image = img
                elements.add_elem(image_element)
        elif args[0] == "resample":
            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    CutPlanner.make_actual(element)
                    element.altered()
            return
        elif args[0] == "dither":
            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    if img.mode == "RGBA":
                        pixel_data = img.load()
                        width, height = img.size
                        for y in range(height):
                            for x in range(width):
                                if pixel_data[x, y][3] == 0:
                                    pixel_data[x, y] = (255, 255, 255, 255)
                    element.image = img.convert("1")
                    element.altered()
        elif args[0] == "remove":
            if len(args) == 1:
                channel(_("Must specify a color, and optionally a distance."))
                return
            distance = 50.0
            color = "White"
            if len(args) >= 2:
                color = args[1]
            try:
                color = Color(color)
            except ValueError:
                channel(_("Color Invalid."))
                return
            if len(args) >= 3:
                try:
                    distance = float(args[2])
                except ValueError:
                    channel(_("Color distance is invalid."))
                    return
            distance_sq = distance * distance

            def dist(pixel):
                r = color.red - pixel[0]
                g = color.green - pixel[1]
                b = color.blue - pixel[2]
                return r * r + g * g + b * b <= distance_sq

            for element in elements.elems(emphasized=True):
                if not isinstance(element, SVGImage):
                    continue
                img = element.image
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
                element.image = img
                element.altered()
        elif args[0] == "add":
            if len(args) == 1:
                channel(_("Must specify a color, to add."))
                return
            color = "White"
            if len(args) >= 2:
                color = args[1]
            try:
                color = Color(color)
            except ValueError:
                channel(_("Color Invalid."))
                return
            pix = (color.red, color.green, color.blue, color.alpha)
            for element in elements.elems(emphasized=True):
                if not isinstance(element, SVGImage):
                    continue
                img = element.image
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
                element.image = img
                element.altered()
        elif args[0] == "crop":
            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    try:
                        left = int(
                            Length(args[1]).value(
                                ppi=1000.0,
                                relative_length=context.bed_width * 39.3701,
                            )
                        )
                        upper = int(
                            Length(args[2]).value(
                                ppi=1000.0,
                                relative_length=context.bed_height * 39.3701,
                            )
                        )
                        right = int(
                            Length(args[3]).value(
                                ppi=1000.0,
                                relative_length=context.bed_width * 39.3701,
                            )
                        )
                        lower = int(
                            Length(args[4]).value(
                                ppi=1000.0,
                                relative_length=context.bed_height * 39.3701,
                            )
                        )
                        element.image = img.crop((left, upper, right, lower))
                        element.image_width = right - left
                        element.image_height = lower - upper
                        element.altered()
                    except (KeyError, ValueError):
                        channel(_("image crop <left> <upper> <right> <lower>"))
            return
        elif args[0] == "contrast":
            for element in elements.elems(emphasized=True):
                from PIL import ImageEnhance

                if isinstance(element, SVGImage):
                    try:

                        factor = float(args[1])
                        img = element.image
                        enhancer = ImageEnhance.Contrast(img)
                        element.image = enhancer.enhance(factor)
                        element.altered()
                        channel(_("Image Contrast Factor: %f") % factor)
                    except (IndexError, ValueError):
                        channel(_("image contrast <factor>"))
            return
        elif args[0] == "brightness":
            for element in elements.elems(emphasized=True):
                from PIL import ImageEnhance

                if isinstance(element, SVGImage):
                    try:
                        factor = float(args[1])
                        img = element.image
                        enhancer = ImageEnhance.Brightness(img)
                        element.image = enhancer.enhance(factor)
                        element.altered()
                        channel(_("Image Brightness Factor: %f") % factor)
                    except (IndexError, ValueError):
                        channel(_("image brightness <factor>"))
            return
        elif args[0] == "color":
            for element in elements.elems(emphasized=True):
                from PIL import ImageEnhance

                if isinstance(element, SVGImage):
                    try:
                        factor = float(args[1])
                        img = element.image
                        enhancer = ImageEnhance.Color(img)
                        element.image = enhancer.enhance(factor)
                        element.altered()
                        channel(_("Image Color Factor: %f") % factor)
                    except (IndexError, ValueError):
                        channel(_("image color <factor>"))
            return
        elif args[0] == "sharpness":
            for element in elements.elems(emphasized=True):
                from PIL import ImageEnhance

                if isinstance(element, SVGImage):
                    try:
                        factor = float(args[1])
                        img = element.image
                        enhancer = ImageEnhance.Sharpness(img)
                        element.image = enhancer.enhance(factor)
                        element.altered()
                        channel(_("Image Sharpness Factor: %f") % factor)
                    except (IndexError, ValueError):
                        channel(_("image sharpness <factor>"))
            return
        elif args[0] == "blur":
            from PIL import ImageFilter

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.filter(filter=ImageFilter.BLUR)
                    element.altered()
                    channel(_("Image Blurred."))
            return
        elif args[0] == "sharpen":
            from PIL import ImageFilter

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.filter(filter=ImageFilter.SHARPEN)
                    element.altered()
                    channel(_("Image Sharpened."))
            return
        elif args[0] == "edge_enhance":
            from PIL import ImageFilter

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.filter(filter=ImageFilter.EDGE_ENHANCE)
                    element.altered()
                    channel(_("Image Edges Enhanced."))
            return
        elif args[0] == "find_edges":
            from PIL import ImageFilter

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.filter(filter=ImageFilter.FIND_EDGES)
                    element.altered()
                    channel(_("Image Edges Found."))
            return
        elif args[0] == "emboss":
            from PIL import ImageFilter

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.filter(filter=ImageFilter.EMBOSS)
                    element.altered()
                    channel(_("Image Embossed."))
            return
        elif args[0] == "smooth":
            from PIL import ImageFilter

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.filter(filter=ImageFilter.SMOOTH)
                    element.altered()
                    channel(_("Image Smoothed."))
            return
        elif args[0] == "contour":
            from PIL import ImageFilter

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.filter(filter=ImageFilter.CONTOUR)
                    element.altered()
                    channel(_("Image Contoured."))
            return
        elif args[0] == "detail":
            from PIL import ImageFilter

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.filter(filter=ImageFilter.DETAIL)
                    element.altered()
                    channel(_("Image Detailed."))
            return
        elif args[0] == "quantize":
            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    try:
                        colors = int(args[1])
                        img = element.image
                        element.image = img.quantize(colors=colors)
                        element.altered()
                        channel(_("Image Quantized to %d colors.") % colors)
                    except (IndexError, ValueError):
                        channel(_("image quantize <colors>"))
            return
        elif args[0] == "solarize":
            from PIL import ImageOps

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    try:
                        threshold = int(args[1])
                        img = element.image
                        element.image = ImageOps.solarize(img, threshold=threshold)
                        element.altered()
                        channel(_("Image Solarized at %d gray.") % threshold)
                    except (IndexError, ValueError):
                        channel(_("image solarize <threshold>"))
            return
        elif args[0] == "invert":
            from PIL import ImageOps

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    original_mode = img.mode
                    if img.mode == "P" or img.mode == "RGBA" or img.mode == "1":
                        img = img.convert("RGB")
                    try:
                        element.image = ImageOps.invert(img)
                        if original_mode == "1":
                            element.image = element.image.convert("1")
                        element.altered()
                        channel(_("Image Inverted."))
                    except OSError:
                        channel(_("Image type cannot be converted. %s") % img.mode)
            return
        elif args[0] == "flip":
            from PIL import ImageOps

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = ImageOps.flip(img)
                    element.altered()
                    channel(_("Image Flipped."))
            return
        elif args[0] == "mirror":
            from PIL import ImageOps

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = ImageOps.mirror(img)
                    element.altered()
                    channel(_("Image Mirrored."))
            return
        elif args[0] == "ccw":
            from PIL import Image

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.transpose(Image.ROTATE_90)
                    element.image_height, element.image_width = (
                        element.image_width,
                        element.image_height,
                    )
                    element.altered()
                    channel(_("Rotated image counterclockwise."))
            return
        elif args[0] == "cw":
            from PIL import Image

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = img.transpose(Image.ROTATE_270)
                    element.image_height, element.image_width = (
                        element.image_width,
                        element.image_height,
                    )
                    element.altered()
                    channel(_("Rotated image clockwise."))
            return
        elif args[0] == "autocontrast":
            from PIL import ImageOps

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    try:
                        cutoff = int(args[1])
                        img = element.image
                        if img.mode == "RGBA":
                            img = img.convert("RGB")
                        element.image = ImageOps.autocontrast(img, cutoff=cutoff)
                        element.altered()
                        channel(_("Image Auto-Contrasted."))
                    except (IndexError, ValueError):
                        channel(_("image autocontrast <cutoff-percent>"))
            return
        elif args[0] == "grayscale" or args[0] == "greyscale":
            from PIL import ImageOps

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = ImageOps.grayscale(img)
                    element.altered()
                    channel(_("Image Grayscale."))
            return
        elif args[0] == "equalize":
            from PIL import ImageOps

            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    img = element.image
                    element.image = ImageOps.equalize(img)
                    element.altered()
                    channel(_("Image Equalized."))
            return
        elif args[0] == "save":
            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    try:
                        img = element.image
                        img.save(args[1])
                        channel(_("Saved: %s") % (args[1]))
                    except IndexError:
                        channel(_("No file given."))
                    except OSError:
                        channel(_("File could not be written / created."))
                    except ValueError:
                        channel(_("Could not determine expected format."))

            return
        elif args[0] == "flatrotary":
            for element in elements.elems(emphasized=True):
                if isinstance(element, SVGImage):
                    points = len(args) - 1
                    im = element.image
                    w, h = im.size
                    from PIL import Image

                    def t(i):
                        return int(i * w / (points - 1))

                    def x(i):
                        return int(w * float(args[i + 1]))

                    boxes = list((t(i), 0, t(i + 1), h) for i in range(points - 1))
                    quads = list(
                        (x(i), 0, x(i), h, x(i + 1), h, x(i + 1), 0)
                        for i in range(points - 1)
                    )
                    mesh = list(zip(boxes, quads))
                    element.image = im.transform(
                        im.size, Image.MESH, mesh, Image.BILINEAR
                    )
                    element.altered()
        elif args[0] == "halftone":
            #  https://stackoverflow.com/questions/10572274/halftone-images-in-python/10575940#10575940
            pass
        else:
            channel(_("Image command unrecognized."))
            return

    @context.console_command(
        "halftone", help="image halftone <diameter> <scale> <angle>"
    )
    def halftone(command, channel, _, args=tuple(), **kwargs):
        """
        Returns list of half-tone images for cmyk image. sample (pixels),
        determines the sample box size from the original image. The maximum
        output dot diameter is given by sample * scale (which is also the number
        of possible dot sizes). So sample=1 will presevere the original image
        resolution, but scale must be >1 to allow variation in dot size."""
        from PIL import Image, ImageDraw, ImageStat
        elements = context.elements
        oversample = 2
        sample = 10
        scale = 1
        angle = 22
        for element in elements.elems(emphasized=True):
            if not isinstance(element, SVGImage):
                continue
            image = element.image
            im = image
            image = image.convert("L")
            image = image.rotate(angle, expand=1)
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
            element.image = half_tone
            element.altered()


class RasterScripts:
    """
    This module serves as the raster scripting routine. It registers raster-scripts and
    processes the known items in known ways. This should be made accessible to the CLI.

    Please note: Lists of instructions and methods are not copyrightable. While the actual text
    itself of various descriptions of procedures can be copyrighted the actual methods and procedures
    cannot be copyrighted themselves. If particular procedures may qualify for or be registered for a
    trademark, the name will be changed to avoid infringing. No patented procedures (eg. seam carving)
    will be permitted.

    I'm happy to take anybody's recipes for raster-preprocessing, while texts of scripts may be copyrighted
    the thing they do cannot be.
    """

    @staticmethod
    def raster_script_gold():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "step": 3}
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
        ops.append({"name": "dither", "enable": True, "type": 0})
        return ops

    @staticmethod
    def raster_script_stipo():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "step": 2}
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
        ops.append({"name": "dither", "enable": True, "type": 0})
        return ops

    @staticmethod
    def raster_script_gravy():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "step": 3}
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
        ops.append({"name": "dither", "enable": True, "type": 0})
        return ops

    @staticmethod
    def raster_script_xin():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "step": 2}
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
        ops.append({"name": "dither", "enable": True, "type": 0})
        return ops

    @staticmethod
    def raster_script_newsy():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "step": 2}
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
        ops.append({"name": "dither", "enable": True, "type": 0})
        return ops

    @staticmethod
    def raster_script_simple():
        ops = list()
        ops.append(
            {"name": "resample", "enable": True, "aspect": True, "units": 0, "step": 3}
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
        ops.append({"name": "dither", "enable": True, "type": 0})
        return ops

    @staticmethod
    def actualize(image, matrix, step_level=1):
        from PIL import Image

        boundary_points = []
        box = image.getbbox()

        top_left = matrix.point_in_matrix_space([box[0], box[1]])
        top_right = matrix.point_in_matrix_space([box[2], box[1]])
        bottom_left = matrix.point_in_matrix_space([box[0], box[3]])
        bottom_right = matrix.point_in_matrix_space([box[2], box[3]])
        boundary_points.append(top_left)
        boundary_points.append(top_right)
        boundary_points.append(bottom_left)
        boundary_points.append(bottom_right)
        xmin = min([e[0] for e in boundary_points])
        ymin = min([e[1] for e in boundary_points])
        xmax = max([e[0] for e in boundary_points])
        ymax = max([e[1] for e in boundary_points])
        bbox = xmin, ymin, xmax, ymax
        element_width = int(ceil(bbox[2] - bbox[0]))
        element_height = int(ceil(bbox[3] - bbox[1]))
        step_scale = 1 / float(step_level)
        tx = bbox[0]
        ty = bbox[1]
        matrix.post_translate(-tx, -ty)
        matrix.post_scale(step_scale, step_scale)
        matrix.inverse()
        if matrix.value_skew_y() != 0.0 or matrix.value_skew_y() != 0.0:
            # If we are rotating an image without alpha, we need to convert it, or the rotation invents black pixels.
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            image = image.transform(
                (element_width, element_height),
                Image.AFFINE,
                (matrix.a, matrix.c, matrix.e, matrix.b, matrix.d, matrix.f),
                resample=Image.BICUBIC,
            )
        else:
            image = image.transform(
                (element_width, element_height),
                Image.AFFINE,
                (matrix.a, matrix.c, matrix.e, matrix.b, matrix.d, matrix.f),
                resample=Image.BICUBIC,
            )
        matrix.reset()

        box = image.getbbox()
        if box is None:
            return image, matrix
        width = box[2] - box[0]
        height = box[3] - box[1]
        if width != element_width and height != element_height:
            image = image.crop(box)
            matrix.post_translate(box[0], box[1])
        # step level requires the new actualized matrix be scaled up.
        matrix.post_scale(step_level, step_level)
        matrix.post_translate(tx, ty)
        return image, matrix

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
    def wizard_image(svg_image, operations):
        image = svg_image.image
        matrix = Matrix(svg_image.transform)
        step = None
        mask = None
        from PIL import Image, ImageOps, ImageFilter, ImageEnhance

        for op in operations:
            name = op["name"]
            if name == "crop":
                try:
                    if op["enable"] and op["bounds"] is not None:
                        crop = op["bounds"]
                        left = int(crop[0])
                        upper = int(crop[1])
                        right = int(crop[2])
                        lower = int(crop[3])
                        image = image.crop((left, upper, right, lower))
                except KeyError:
                    pass
            if name == "resample":
                try:
                    if op["enable"]:
                        image, matrix = RasterScripts.actualize(
                            image, matrix, step_level=op["step"]
                        )
                        step = op["step"]
                except KeyError:
                    pass
            if name == "grayscale":
                try:
                    if op["enable"]:
                        try:
                            r = op["red"] * 0.299
                            g = op["green"] * 0.587
                            b = op["blue"] * 0.114
                            v = op["lightness"]
                            c = r + g + b
                            try:
                                c /= v
                                r = r / c
                                g = g / c
                                b = b / c
                            except ZeroDivisionError:
                                pass
                            m = [r, g, b, 1.0]
                            if image.mode != "L":
                                if image.mode in ("P", "1", "CMYK", "LAB"):
                                    image = image.convert("RGBA")
                                if op["invert"]:
                                    color = 0, 0, 0
                                    c8 = 0
                                else:
                                    color = 255, 255, 255
                                    c8 = 255
                                if image.mode == "RGBA":
                                    background = Image.new("RGB", image.size, color)
                                    background.paste(image, mask=image.getchannel("A"))
                                    image = background
                                image = image.convert("L", matrix=m)

                                def mask_filter(e):
                                    if e == c8:
                                        return 0
                                    else:
                                        return 255

                                mask = image.point(
                                    mask_filter
                                )  # Makes a mask out of Alpha or pure mask color.
                            if op["invert"]:
                                image = ImageOps.invert(image)
                        except (KeyError, OSError):
                            pass

                except KeyError:
                    pass
            if name == "edge_enhance":
                try:
                    if op["enable"]:
                        if image.mode == "P":
                            image = image.convert("L")
                        image = image.filter(filter=ImageFilter.EDGE_ENHANCE)
                except KeyError:
                    pass
            if name == "auto_contrast":
                try:
                    if op["enable"]:
                        if image.mode != "P":
                            image = image.convert("L")
                        image = ImageOps.autocontrast(image, cutoff=op["cutoff"])
                except KeyError:
                    pass
            if name == "tone":
                try:
                    if op["enable"] and op["values"] is not None:
                        if image.mode == "L":
                            image = image.convert("P")
                            tone_values = op["values"]
                            if op["type"] == "spline":
                                spline = RasterScripts.spline(tone_values)
                            else:
                                tone_values = [q for q in tone_values if q is not None]
                                spline = RasterScripts.line(tone_values)
                            if len(spline) < 256:
                                spline.extend([255] * (256 - len(spline)))
                            if len(spline) > 256:
                                spline = spline[:256]
                            image = image.point(spline)
                            if image.mode != "L":
                                image = image.convert("L")
                except KeyError:
                    pass
            if name == "contrast":
                try:
                    if op["enable"]:
                        if op["contrast"] is not None and op["brightness"] is not None:
                            contrast = ImageEnhance.Contrast(image)
                            c = (op["contrast"] + 128.0) / 128.0
                            image = contrast.enhance(c)

                            brightness = ImageEnhance.Brightness(image)
                            b = (op["brightness"] + 128.0) / 128.0
                            image = brightness.enhance(b)
                except KeyError:
                    pass
            if name == "gamma":
                try:
                    if op["enable"] and op["factor"] is not None:
                        if image.mode == "L":
                            gamma_factor = float(op["factor"])

                            def crimp(px):
                                px = int(round(px))
                                if px < 0:
                                    return 0
                                if px > 255:
                                    return 255
                                return px

                            if gamma_factor == 0:
                                gamma_lut = [0] * 256
                            else:
                                gamma_lut = [
                                    crimp(pow(i / 255, (1.0 / gamma_factor)) * 255)
                                    for i in range(256)
                                ]
                            image = image.point(gamma_lut)
                            if image.mode != "L":
                                image = image.convert("L")
                except KeyError:
                    pass
            if name == "unsharp_mask":
                try:
                    if (
                        op["enable"]
                        and op["percent"] is not None
                        and op["radius"] is not None
                        and op["threshold"] is not None
                    ):
                        unsharp = ImageFilter.UnsharpMask(
                            radius=op["radius"],
                            percent=op["percent"],
                            threshold=op["threshold"],
                        )
                        image = image.filter(unsharp)
                except (KeyError, ValueError):  # Value error if wrong type of image.
                    pass
            if name == "dither":
                try:
                    if op["enable"] and op["type"] is not None:
                        if mask is not None:
                            background = Image.new(image.mode, image.size, "white")
                            background.paste(image, mask=mask)
                            image = background  # Mask exists use it to remove any pixels that were pure reject.
                        if image.mode == "RGBA":
                            pixel_data = image.load()
                            width, height = image.size
                            for y in range(height):
                                for x in range(width):
                                    if pixel_data[x, y][3] == 0:
                                        pixel_data[x, y] = (255, 255, 255, 255)
                        image = image.convert("1")
                except KeyError:
                    pass
            if name == "halftone":
                try:
                    if op["enable"]:
                        image = RasterScripts.halftone(
                            image,
                            sample=op["sample"],
                            angle=op["angle"],
                            oversample=op["oversample"],
                            black=op["black"],
                        )
                except KeyError:
                    pass

        return image, matrix, step

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
        :param p: points to be quad spline interpolated.
        :return: integer y values for given spline points.
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
        yield "GIF Format", ("gif",), "image/gif"
        yield "Icon Format", ("ico",), "image/ico"
        yield "JPEG Format", ("jpg", "jpeg", "jpe"), "image/jpeg"
        yield "Webp Format", ("webp",), "image/webp"

    @staticmethod
    def load(context, pathname, **kwargs):
        basename = ospath.basename(pathname)

        image = SVGImage(
            {"href": pathname, "width": "100%", "height": "100%", "id": basename}
        )
        image.load()
        try:
            context.setting(bool, "image_dpi", True)
            if context.image_dpi:
                dpi = image.image.info["dpi"]
                if isinstance(dpi, tuple):
                    image *= "scale(%f,%f)" % (1000.0 / dpi[0], 1000.0 / dpi[1])
        except (KeyError, IndexError):
            pass
        return [image], None, None, pathname, basename
