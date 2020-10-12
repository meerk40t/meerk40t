
from Kernel import Modifier
from svgelements import *


class ImageTools(Modifier):
    """
    ImageTools mostly provides the image functionality to the console. It should be loaded in the root context.
    This functionality will largely depend on PIL/Pillow for the image command subfunctions.
    """

    def __init__(self, context, name=None, channel=None, *args, **kwargs):
        Modifier.__init__(self, context, name, channel)

    def attach(self, channel=None):
        context = self.context
        kernel = context._kernel
        elements = context.elements
        _ = kernel.translation

        def image(command, *args):
            if len(args) == 0:
                yield _('----------')
                yield _('Images:')
                i = 0
                for element in elements.elems():
                    if not isinstance(element, SVGImage):
                        continue
                    name = str(element)
                    if len(name) > 50:
                        name = name[:50] + '...'
                    yield '%d: (%d, %d) %s, %s' % (i,
                                                   element.image_width,
                                                   element.image_height,
                                                   element.image.mode,
                                                   name)
                    i += 1
                yield _('----------')
                return
            if not elements.has_emphasis():
                yield _('No selected images.')
                return
            elif args[0] == 'wizard':
                if len(args) == 1:
                    try:
                        for script_name in context.match('raster_script', True):
                            yield _('Raster Script: %s') % script_name
                    except KeyError:
                        yield _('No Raster Scripts Found.')
                    return
                try:
                    script = context.registered['raster_script/%s' % args[1]]
                except KeyError:
                    yield _('Raster Script %s is not registered.') % args[1]
                    return
                from RasterScripts import RasterScripts
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
                yield _('Unlocking Elements...')
                for element in elements.elems(emphasized=True):
                    try:
                        if element.lock:
                            yield "Unlocked: %s" % str(element)
                            element.lock = False
                        else:
                            yield _('Element was not locked: %s') % str(element)
                    except AttributeError:
                        yield _('Element was not locked: %s') % str(element)
                return
            elif args[0] == 'threshold':
                try:
                    threshold_min = float(args[1])
                    threshold_max = float(args[2])
                except (ValueError, IndexError):
                    yield _('Threshold values improper.')
                    return
                divide = (threshold_max - threshold_min) / 255.0
                for element in elements.elems(emphasized=True):
                    if not isinstance(element, SVGImage):
                        continue
                    image_element = copy(element)
                    image_element.image = image_element.image.copy()
                    if OperationPreprocessor.needs_actualization(image_element):
                        OperationPreprocessor.make_actual(image_element)
                    img = image_element.image
                    new_data = img.load()
                    width, height = img.size
                    for y in range(height):
                        for x in range(width):
                            pixel = new_data[x, y]
                            if pixel[3] == 0:
                                new_data[x, y] = (255, 255, 255, 255)
                                continue
                            gray = (pixel[0] + pixel[1] + pixel[2]) / 3.0
                            if threshold_min >= gray:
                                new_data[x, y] = (0, 0, 0, 255)
                            elif threshold_max < gray:
                                new_data[x, y] = (255, 255, 255, 255)
                            else:  # threshold_min <= grey < threshold_max
                                v = gray - threshold_min
                                v *= divide
                                v = int(round(v))
                                new_data[x, y] = (v, v, v, 255)
                    elements.add_elem(image_element)
            elif args[0] == 'resample':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        OperationPreprocessor.make_actual(element)
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
                    yield _('Must specify a color, and optionally a distance.')
                    return
                distance = 50.0
                color = "White"
                if len(args) >= 2:
                    color = args[1]
                try:
                    color = Color(color)
                except ValueError:
                    yield _('Color Invalid.')
                    return
                if len(args) >= 3:
                    try:
                        distance = float(args[2])
                    except ValueError:
                        yield _('Color distance is invalid.')
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
                    yield _('Must specify a color, to add.')
                    return
                color = "White"
                if len(args) >= 2:
                    color = args[1]
                try:
                    color = Color(color)
                except ValueError:
                    yield _('Color Invalid.')
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
                            left = int(args[1])
                            upper = int(args[2])
                            right = int(args[3])
                            lower = int(args[4])
                            element.image = img.crop((left, upper, right, lower))
                            element.image_width = right - left
                            element.image_height = lower - upper
                            element.altered()
                        except (KeyError, ValueError):
                            yield _('image crop <left> <upper> <right> <lower>')
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
                            yield _('Image Contrast Factor: %f') % factor
                        except (IndexError, ValueError):
                            yield _('image contrast <factor>')
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
                            yield _('Image Brightness Factor: %f') % factor
                        except (IndexError, ValueError):
                            yield _('image brightness <factor>')
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
                            yield _('Image Color Factor: %f') % factor
                        except (IndexError, ValueError):
                            yield _('image color <factor>')
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
                            yield _('Image Sharpness Factor: %f') % factor
                        except (IndexError, ValueError):
                            yield _('image sharpness <factor>')
                return
            elif args[0] == 'blur':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.BLUR)
                        element.altered()
                        yield _('Image Blurred.')
                return
            elif args[0] == 'sharpen':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.SHARPEN)
                        element.altered()
                        yield _('Image Sharpened.')
                return
            elif args[0] == 'edge_enhance':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.EDGE_ENHANCE)
                        element.altered()
                        yield _('Image Edges Enhanced.')
                return
            elif args[0] == 'find_edges':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.FIND_EDGES)
                        element.altered()
                        yield _('Image Edges Found.')
                return
            elif args[0] == 'emboss':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.EMBOSS)
                        element.altered()
                        yield _('Image Embossed.')
                return
            elif args[0] == 'smooth':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.SMOOTH)
                        element.altered()
                        yield _('Image Smoothed.')
                return
            elif args[0] == 'contour':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.CONTOUR)
                        element.altered()
                        yield _('Image Contoured.')
                return
            elif args[0] == 'detail':
                from PIL import ImageFilter
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.filter(filter=ImageFilter.DETAIL)
                        element.altered()
                        yield _('Image Detailed.')
                return
            elif args[0] == 'quantize':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            colors = int(args[1])
                            img = element.image
                            element.image = img.quantize(colors=colors)
                            element.altered()
                            yield _('Image Quantized to %d colors.') % colors
                        except (IndexError, ValueError):
                            yield _('image quantize <colors>')
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
                            yield _('Image Solarized at %d gray.') % threshold
                        except (IndexError, ValueError):
                            yield _('image solarize <threshold>')
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
                            yield _('Image Inverted.')
                        except OSError:
                            yield _('Image type cannot be converted. %s') % img.mode
                return
            elif args[0] == 'flip':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.flip(img)
                        element.altered()
                        yield _('Image Flipped.')
                return
            elif args[0] == 'mirror':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.mirror(img)
                        element.altered()
                        yield _('Image Mirrored.')
                return
            elif args[0] == 'ccw':
                from PIL import Image
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.transpose(Image.ROTATE_90)
                        element.image_height, element.image_width = element.image_width, element.image_height
                        element.altered()
                        yield _('Rotated image counterclockwise.')
                return
            elif args[0] == 'cw':
                from PIL import Image
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = img.transpose(Image.ROTATE_270)
                        element.image_height, element.image_width = element.image_width, element.image_height
                        element.altered()
                        yield _('Rotated image clockwise.')
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
                            yield _('Image Auto-Contrasted.')
                        except (IndexError, ValueError):
                            yield _('image autocontrast <cutoff-percent>')
                return
            elif args[0] == 'grayscale' or args[0] == 'greyscale':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.grayscale(img)
                        element.altered()
                        yield _('Image Grayscale.')
                return
            elif args[0] == 'equalize':
                from PIL import ImageOps
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        img = element.image
                        element.image = ImageOps.equalize(img)
                        element.altered()
                        yield _('Image Equalized.')
                return
            elif args[0] == 'save':
                for element in elements.elems(emphasized=True):
                    if isinstance(element, SVGImage):
                        try:
                            img = element.image
                            img.save(args[1])
                            yield _('Saved: %s') % (args[1])
                        except IndexError:
                            yield _('No file given.')
                        except OSError:
                            yield _('File could not be written / created.')
                        except ValueError:
                            yield _('Could not determine expected format.')

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
                yield _('Image command unrecognized.')
                return

        kernel.register('command/image', image)

        def halftone(command, *args):
            '''Returns list of half-tone images for cmyk image. sample (pixels),
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

        kernel.register('command/halftone', halftone)
        kernel.register('command-help/halftone', 'image halftone <diameter> <scale> <angle> ')
