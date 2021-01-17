from copy import copy

from . kernel import Modifier, console_command
from . cutplanner import CutPlanner
from . svgelements import SVGImage, Color, Length, Path


class ImageTools(Modifier):
    """
    ImageTools mostly provides the image functionality to the console. It should be loaded in the root context.
    This functionality will largely depend on PIL/Pillow for the image command subfunctions.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)

    def attach(self, *a, **kwargs):
        context = self.context
        kernel = context._kernel
        elements = context.elements
        _ = kernel.translation

        @console_command(self.context, 'image', help='image <operation>')
        def image(command, channel, _, args=tuple(), **kwargs):
            if len(args) == 0:
                channel(_('----------'))
                channel(_('Images:'))
                i = 0
                for element in elements.elems():
                    if not isinstance(element, SVGImage):
                        continue
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield channel('%d: (%d, %d) %s, %s' % (i,
                                                   element.image_width,
                                                   element.image_height,
                                                   element.image.mode,
                                                   name))
                    i += 1
                channel(_('----------'))
                return
            if not elements.has_emphasis():
                channel(_('No selected images.'))
                return
            elif args[0] == 'path':
                for element in list(elements.elems(emphasized=True)):
                    bounds = element.bbox()
                    p = Path()
                    p.move((bounds[0], bounds[1]),
                            (bounds[0], bounds[3]),
                            (bounds[2], bounds[3]),
                           (bounds[2], bounds[1]))
                    p.closed()
                    elements.add_element(p)
                return
            elif args[0] == 'wizard':
                if len(args) == 1:
                    try:
                        for script_name in context.match('raster_script', True):
                            channel(_('Raster Script: %s') % script_name)
                    except KeyError:
                        channel(_('No Raster Scripts Found.'))
                    return
                try:
                    script = context.registered['raster_script/%s' % args[1]]
                except KeyError:
                    channel(_('Raster Script %s is not registered.') % args[1])
                    return
                from rasterscripts import RasterScripts
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        element.image, element.transform, step = RasterScripts.wizard_image(element, script)
                        if step is not None:
                            element.values['raster_step'] = step
                        element.image_width, element.image_height = element.image.size
                        element.lock = True
                        element.altered()
                return
            elif args[0] == 'unlock':
                channel(_('Unlocking Elements...'))
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            channel("Unlocked: %s" % str(element))
                            element.lock = False
                        else:
                            channel(_('Element was not locked: %s') % str(element))
                    except AttributeError:
                        channel(_('Element was not locked: %s') % str(element))
                return
            elif args[0] == 'threshold':
                try:
                    threshold_min = float(args[1])
                    threshold_max = float(args[2])
                except (ValueError, IndexError):
                    channel(_('Threshold values improper.'))
                    return
                divide = (threshold_max - threshold_min) / 255.0
                for element in elements.elems(emphasized=True):
                    if not isinstance(element, SVGImage):
                        continue
                    image_element = copy(element)
                    image_element.image = image_element.image.copy()
                    try:
                        from OperationPreprocessor import OperationPreprocessor
                    except ImportError:
                        channel("No Render Engine Installed.")
                        return
                    if OperationPreprocessor.needs_actualization(image_element):
                        OperationPreprocessor.make_actual(image_element)
                    img = image_element.image
                    img = img.convert('L')

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
            elif args[0] == 'resample':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        CutPlanner.make_actual(element)
                        element.altered()
                return
            elif args[0] == 'dither':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        if img.mode == 'RGBA':
                            pixel_data = img.load()
                            width, height = img.size
                            for y in range(height):
                                for x in range(width):
                                    if pixel_data[x, y][3] == 0:
                                        pixel_data[x, y] = (255, 255, 255, 255)
                        element.image = img.convert("1")
                        element.altered()
            elif args[0] == 'remove':
                if len(args) == 1:
                    channel(_('Must specify a color, and optionally a distance.'))
                    return
                distance = 50.0
                color = "White"
                if len(args) >= 2:
                    color = args[1]
                try:
                    color = Color(color)
                except ValueError:
                    channel(_('Color Invalid.'))
                    return
                if len(args) >= 3:
                    try:
                        distance = float(args[2])
                    except ValueError:
                        channel(_('Color distance is invalid.'))
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
                        img = img.convert('RGBA')
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
            elif args[0] == 'add':
                if len(args) == 1:
                    channel(_('Must specify a color, to add.'))
                    return
                color = "White"
                if len(args) >= 2:
                    color = args[1]
                try:
                    color = Color(color)
                except ValueError:
                    channel(_('Color Invalid.'))
                    return
                pix = (color.red, color.green, color.blue, color.alpha)
                for element in elements.elems(emphasized=True):
                    if not isinstance(element, SVGImage):
                        continue
                    img = element.image
                    if img.mode != "RGBA":
                        img = img.convert('RGBA')
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
            elif args[0] == 'crop':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        try:
                            left = int(
                                Length(args[1]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701))
                            upper = int(
                                Length(args[2]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701))
                            right = int(
                                Length(args[3]).value(ppi=1000.0, relative_length=self.context.bed_width * 39.3701))
                            lower = int(
                                Length(args[4]).value(ppi=1000.0, relative_length=self.context.bed_height * 39.3701))
                            element.image = img.crop((left, upper, right, lower))
                            element.image_width = right - left
                            element.image_height = lower - upper
                            element.altered()
                        except (KeyError, ValueError):
                            channel(_('image crop <left> <upper> <right> <lower>'))
                return
            elif args[0] == 'contrast':
                for element in elements.elems(emphasized=True):
                    from PIL import ImageEnhance
                    if isinstance(element, SVGImage):
                        try:

                            factor = float(args[1])
                            img = element.image
                            enhancer = ImageEnhance.Contrast(img)
                            element.image = enhancer.enhance(factor)
                            element.altered()
                            channel(_('Image Contrast Factor: %f') % factor)
                        except (IndexError, ValueError):
                            channel(_('image contrast <factor>'))
                return
            elif args[0] == 'brightness':
                for element in elements.elems(emphasized=True):
                    from PIL import ImageEnhance
                    if isinstance(element, SVGImage):
                        try:
                            factor = float(args[1])
                            img = element.image
                            enhancer = ImageEnhance.Brightness(img)
                            element.image = enhancer.enhance(factor)
                            element.altered()
                            channel(_('Image Brightness Factor: %f') % factor)
                        except (IndexError, ValueError):
                            channel(_('image brightness <factor>'))
                return
            elif args[0] == 'color':
                for element in elements.elems(emphasized=True):
                    from PIL import ImageEnhance
                    if isinstance(element, SVGImage):
                        try:
                            factor = float(args[1])
                            img = element.image
                            enhancer = ImageEnhance.Color(img)
                            element.image = enhancer.enhance(factor)
                            element.altered()
                            channel(_('Image Color Factor: %f') % factor)
                        except (IndexError, ValueError):
                            channel(_('image color <factor>'))
                return
            elif args[0] == 'sharpness':
                for element in elements.elems(emphasized=True):
                    from PIL import ImageEnhance
                    if isinstance(element, SVGImage):
                        try:
                            factor = float(args[1])
                            img = element.image
                            enhancer = ImageEnhance.Sharpness(img)
                            element.image = enhancer.enhance(factor)
                            element.altered()
                            channel(_('Image Sharpness Factor: %f') % factor)
                        except (IndexError, ValueError):
                            channel(_('image sharpness <factor>'))
                return
            elif args[0] == 'blur':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.BLUR)
                        element.altered()
                        channel(_('Image Blurred.'))
                return
            elif args[0] == 'sharpen':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.SHARPEN)
                        element.altered()
                        channel(_('Image Sharpened.'))
                return
            elif args[0] == 'edge_enhance':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.EDGE_ENHANCE)
                        element.altered()
                        channel(_('Image Edges Enhanced.'))
                return
            elif args[0] == 'find_edges':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.FIND_EDGES)
                        element.altered()
                        channel(_('Image Edges Found.'))
                return
            elif args[0] == 'emboss':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.EMBOSS)
                        element.altered()
                        channel(_('Image Embossed.'))
                return
            elif args[0] == 'smooth':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.SMOOTH)
                        element.altered()
                        channel(_('Image Smoothed.'))
                return
            elif args[0] == 'contour':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.CONTOUR)
                        element.altered()
                        channel(_('Image Contoured.'))
                return
            elif args[0] == 'detail':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.DETAIL)
                        element.altered()
                        channel(_('Image Detailed.'))
                return
            elif args[0] == 'quantize':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            colors = int(args[1])
                            img = element.image
                            element.image = img.quantize(colors=colors)
                            element.altered()
                            channel(_('Image Quantized to %d colors.') % colors)
                        except (IndexError, ValueError):
                            channel(_('image quantize <colors>'))
                return
            elif args[0] == 'solarize':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            threshold = int(args[1])
                            img = element.image
                            element.image = ImageOps.solarize(img, threshold=threshold)
                            element.altered()
                            channel(_('Image Solarized at %d gray.') % threshold)
                        except (IndexError, ValueError):
                            channel(_('image solarize <threshold>'))
                return
            elif args[0] == 'invert':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        original_mode = img.mode
                        if img.mode == 'P' or img.mode == 'RGBA' or img.mode == '1':
                            img = img.convert('RGB')
                        try:
                            element.image = ImageOps.invert(img)
                            if original_mode == '1':
                                element.image = element.image.convert('1')
                            element.altered()
                            channel(_('Image Inverted.'))
                        except OSError:
                            channel(_('Image type cannot be converted. %s') % img.mode)
                return
            elif args[0] == 'flip':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.flip(img)
                        element.altered()
                        channel(_('Image Flipped.'))
                return
            elif args[0] == 'mirror':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.mirror(img)
                        element.altered()
                        channel(_('Image Mirrored.'))
                return
            elif args[0] == 'ccw':
                from PIL import Image
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.transpose(Image.ROTATE_90)
                        element.image_height, element.image_width = element.image_width, element.image_height
                        element.altered()
                        channel(_('Rotated image counterclockwise.'))
                return
            elif args[0] == 'cw':
                from PIL import Image
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.transpose(Image.ROTATE_270)
                        element.image_height, element.image_width = element.image_width, element.image_height
                        element.altered()
                        channel(_('Rotated image clockwise.'))
                return
            elif args[0] == 'autocontrast':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            cutoff = int(args[1])
                            img = element.image
                            if img.mode == 'RGBA':
                                img = img.convert('RGB')
                            element.image = ImageOps.autocontrast(img, cutoff=cutoff)
                            element.altered()
                            channel(_('Image Auto-Contrasted.'))
                        except (IndexError, ValueError):
                            channel(_('image autocontrast <cutoff-percent>'))
                return
            elif args[0] == 'grayscale' or args[0] == 'greyscale':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.grayscale(img)
                        element.altered()
                        channel(_('Image Grayscale.'))
                return
            elif args[0] == 'equalize':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.equalize(img)
                        element.altered()
                        channel(_('Image Equalized.'))
                return
            elif args[0] == 'save':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            img = element.image
                            img.save(args[1])
                            channel(_('Saved: %s') % (args[1]))
                        except IndexError:
                            channel(_('No file given.'))
                        except OSError:
                            channel(_('File could not be written / created.'))
                        except ValueError:
                            channel(_('Could not determine expected format.'))

                return
            elif args[0] == 'flatrotary':
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
                        quads = list((x(i), 0, x(i), h, x(i + 1), h, x(i + 1), 0) for i in range(points - 1))
                        mesh = list(zip(boxes, quads))
                        element.image = im.transform(im.size, Image.MESH,
                                                     mesh,
                                                     Image.BILINEAR)
                        element.altered()
            elif args[0] == 'halftone':
                #  https://stackoverflow.com/questions/10572274/halftone-images-in-python/10575940#10575940
                pass
            else:
                channel(_('Image command unrecognized.'))
                return

        @console_command(self.context, 'halftone', help='image halftone <diameter> <scale> <angle>')
        def halftone(command, channel, _, args=tuple(), **kwargs):
            '''
            Returns list of half-tone images for cmyk image. sample (pixels),
            determines the sample box size from the original image. The maximum
            output dot diameter is given by sample * scale (which is also the number
            of possible dot sizes). So sample=1 will presevere the original image
            resolution, but scale must be >1 to allow variation in dot size.'''
            from PIL import Image, ImageDraw, ImageStat
            oversample = 2
            sample = 10
            scale = 1
            angle = 22
            for element in elements.elems(emphasized=True):
                if not isinstance(element, SVGImage):
                    continue
                image = element.image
                im = image
                image = image.convert('L')
                image = image.rotate(angle, expand=1)
                size = image.size[0] * scale, image.size[1] * scale
                half_tone = Image.new('L', size)
                draw = ImageDraw.Draw(half_tone)
                for x in range(0, image.size[0], sample):
                    for y in range(0, image.size[1], sample):
                        box = image.crop(
                            (x - oversample, y - oversample, x + sample + oversample, y + sample + oversample))
                        stat = ImageStat.Stat(box)
                        diameter = (stat.mean[0] / 255) ** 0.5
                        edge = 0.5 * (1 - diameter)
                        x_pos, y_pos = (x + edge) * scale, (y + edge) * scale
                        box_edge = sample * diameter * scale
                        draw.ellipse((x_pos, y_pos, x_pos + box_edge, y_pos + box_edge), fill=255)
                half_tone = half_tone.rotate(-angle, expand=1)
                width_half, height_half = half_tone.size
                xx = (width_half - im.size[0] * scale) / 2
                yy = (height_half - im.size[1] * scale) / 2
                half_tone = half_tone.crop((xx, yy, xx + im.size[0] * scale, yy + im.size[1] * scale))
            element.image = half_tone
            element.altered()

