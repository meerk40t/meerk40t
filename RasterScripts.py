from Kernel import Module
from math import ceil

from svgelements import Matrix


class RasterScripts(Module):
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
    def __init__(self):
        Module.__init__(self)

    @staticmethod
    def sub_register(device):
        device.register('raster_script', "Gold", RasterScripts.raster_script_gold())
        device.register('raster_script', "Stipo", RasterScripts.raster_script_stipo())
        device.register('raster_script', "Gravy", RasterScripts.raster_script_gravy())
        device.register('raster_script', "Xin", RasterScripts.raster_script_xin())

    @staticmethod
    def raster_script_gold():
        ops = list()
        # ops.append({
        #     'name': 'crop',
        #     'enable': False,
        #     'bounds': (0, 0, 100, 100)
        # })
        ops.append({
            'name': 'grayscale',
            'enable': True,
            'invert': False,
            'red': 1.0,
            'green': 1.0,
            'blue': 1.0,
            'lightness': 1.0
        })
        ops.append({
            'name': 'resample',
            'enable': True,
            'aspect': True,
            'units': 0,
            'step': 3
        })
        ops.append({
            'name': 'contrast',
            'enable': True,
            'contrast': 25,
            'brightness': 25,
        })
        ops.append({
            'name': 'unsharp_mask',
            'enable': True,
            'percent': 500,
            'radius': 4,
            'threshold': 0
        })
        ops.append({
            'name': 'unsharp_mask',
            'enable': False,
            'percent': 150,
            'radius': 1,
            'threshold': 0
        })
        ops.append({
            'name': 'dither',
            'enable': True,
            'type': 0
        })
        return ops

    @staticmethod
    def raster_script_stipo():
        ops = list()
        # ops.append({
        #     'name': 'crop',
        #     'enable': False,
        #     'bounds': (0, 0, 100, 100)
        # })
        ops.append({
            'name': 'resample',
            'enable': True,
            'aspect': True,
            'units': 0,
            'step': 2
        })
        ops.append({
            'name': 'grayscale',
            'enable': True,
            'invert': False,
            'red': 1.0,
            'green': 1.0,
            'blue': 1.0,
            'lightness': 1.0
        })
        ops.append({
            'name': 'tone',
            'type': 'spline',
            'enable': True,
            'values': [[0, 0], [100, 150], [255, 255]]
        })
        ops.append({
            'name': 'gamma',
            'enable': True,
            'factor': 3.5
        })
        ops.append({
            'name': 'unsharp_mask',
            'enable': True,
            'percent': 500,
            'radius': 20,
            'threshold': 6
        })
        ops.append({
            'name': 'dither',
            'enable': True,
            'type': 0
        })
        return ops

    @staticmethod
    def raster_script_gravy():
        ops = list()
        ops.append({
            'name': 'resample',
            'enable': True,
            'aspect': True,
            'units': 0,
            'step': 3
        })
        ops.append({
            'name': 'edge_enhance',
            'enable': False
        })
        ops.append({
            'name': 'auto_contrast',
            'enable': True,
            'cutoff': 3
        })
        ops.append({
            'name': 'grayscale',
            'enable': True,
            'invert': False,
            'red': 1.0,
            'green': 1.0,
            'blue': 1.0,
            'lightness': 1.0
        })
        ops.append({
            'name': 'unsharp_mask',
            'enable': True,
            'percent': 500,
            'radius': 4,
            'threshold': 0
        })
        ops.append({
            'name': 'tone',
            'type': 'line',
            'enable': True,
            'values': [(2, 32), (9, 50), (30, 84), (40, 99), (76, 144), (101, 170),
                       (126, 193), (156, 214), (181, 230), (206, 246), (256, 254)]

        })
        ops.append({
            'name': 'dither',
            'enable': True,
            'type': 0
        })
        return ops

    @staticmethod
    def raster_script_xin():
        ops = list()

        ops.append({
            'name': 'resample',
            'enable': True,
            'aspect': True,
            'units': 0,
            'step': 2
        })
        ops.append({
            'name': 'grayscale',
            'enable': True,
            'invert': False,
            'red': 1.0,
            'green': 1.0,
            'blue': 1.0,
            'lightness': 1.0
        })
        ops.append({
            'name': 'tone',
            'type': 'spline',
            'enable': True,
            'values': [[0, 0], [100, 125], [255, 255]]
        })
        ops.append({
            'name': 'unsharp_mask',
            'enable': True,
            'percent': 100,
            'radius': 8,
            'threshold': 0
        })
        ops.append({
            'name': 'dither',
            'enable': True,
            'type': 0
        })
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

        tx = bbox[0]
        ty = bbox[1]
        matrix.post_translate(-tx, -ty)
        element_width = int(ceil(bbox[2] - bbox[0]))
        element_height = int(ceil(bbox[3] - bbox[1]))
        step_scale = 1 / float(step_level)
        matrix.pre_scale(step_scale, step_scale)
        matrix.inverse()
        if (matrix.value_skew_y() != 0.0 or matrix.value_skew_y() != 0.0) and image.mode != 'RGBA':
            # If we are rotating an image without alpha, we need to convert it, or the rotation invents black pixels.
            image = image.convert('RGBA')
        image = image.transform((element_width, element_height), Image.AFFINE,
                                        (matrix.a, matrix.c, matrix.e, matrix.b, matrix.d, matrix.f),
                                        resample=Image.BICUBIC)
        matrix.reset()

        box = image.getbbox()
        width = box[2] - box[0]
        height = box[3] - box[1]
        if width != element_width and height != element_height:
            image = image.crop(box)
            box = image.getbbox()
            matrix.post_translate(box[0], box[1])
        # step level requires the new actualized matrix be scaled up.
        matrix.post_scale(step_level, step_level)
        matrix.post_translate(tx, ty)
        return image, matrix

    @staticmethod
    def wizard_image(svg_image, operations):
        image = svg_image.image
        matrix = Matrix(svg_image.transform)
        step = None
        from PIL import ImageOps, ImageFilter, ImageEnhance
        for op in operations:
            name = op['name']
            if name == 'crop':
                try:
                    if op['enable'] and op['bounds'] is not None:
                        crop = op['bounds']
                        left = int(crop[0])
                        upper = int(crop[1])
                        right = int(crop[2])
                        lower = int(crop[3])
                        image = image.crop((left, upper, right, lower))
                except KeyError:
                    pass
            if name == 'resample':
                try:
                    if op['enable']:
                        image, matrix = RasterScripts.actualize(image, matrix, step_level=op['step'])

                        step = op['step']
                except KeyError:
                    pass
            if name == 'grayscale':
                try:
                    if op['enable']:
                        try:
                            r = op['red'] * 0.299
                            g = op['green'] * 0.587
                            b = op['blue'] * 0.114
                            v = op['lightness']
                            c = r + g + b
                            try:
                                c /= v
                                r = r/c
                                g = g/c
                                b = b/c
                            except ZeroDivisionError:
                                pass
                            m = [r,g,b,1.0]
                            if image.mode == 'RGBA':
                                image = image.convert('RGB')
                            image = image.convert("L", matrix=m)
                            if op['invert']:
                                image = ImageOps.invert(image)
                        except (KeyError, OSError):
                            pass

                except KeyError:
                    pass
            if name == 'edge_enhance':
                try:
                    if image.mode == 'P':
                        image = image.convert('L')
                    if op['enable']:
                        image = image.filter(filter=ImageFilter.EDGE_ENHANCE)
                except KeyError:
                    pass
            if name == 'auto_contrast':
                try:
                    if image.mode != 'P':
                        image = image.convert('L')
                    if op['enable']:
                        image = ImageOps.autocontrast(image, cutoff=op['cutoff'])
                except KeyError:
                    pass
            if name == 'tone':
                try:
                    if op['enable'] and op['values'] is not None:
                        if image.mode == 'L':
                            image = image.convert('P')
                            tone_values = op['values']
                            if op['type'] == 'spline':
                                spline = RasterScripts.spline(tone_values)
                            else:
                                tone_values = [q for q in tone_values if q is not None]
                                spline = RasterScripts.line(tone_values)
                            if len(spline) < 256:
                                spline.extend([255] * (256-len(spline)))
                            if len(spline) > 256:
                                spline = spline[:256]
                            image = image.point(spline)
                            if image.mode != 'L':
                                image = image.convert('L')
                except KeyError:
                    pass
            if name == 'contrast':
                try:
                    if op['enable']:
                        if op['contrast'] is not None and op['brightness'] is not None:
                            contrast = ImageEnhance.Contrast(image)
                            c = (op['contrast'] + 128.0) / 128.0
                            image = contrast.enhance(c)

                            brightness = ImageEnhance.Brightness(image)
                            b = (op['brightness'] + 128.0) / 128.0
                            image = brightness.enhance(b)
                except KeyError:
                    pass
            if name == 'gamma':
                try:
                    if op['enable'] and op['factor'] is not None:
                        if image.mode == 'L':
                            gamma_factor = float(op['factor'])

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
                                gamma_lut = [crimp(pow(i / 255, (1.0 / gamma_factor)) * 255) for i in range(256)]
                            image = image.point(gamma_lut)
                            if image.mode != 'L':
                                image = image.convert('L')
                except KeyError:
                    pass
            if name == 'unsharp_mask':
                try:
                    if op['enable'] and \
                            op['percent'] is not None and \
                            op['radius'] is not None and \
                            op['threshold'] is not None:
                        unsharp = ImageFilter.UnsharpMask(radius=op['radius'], percent=op['percent'],
                                                          threshold=op['threshold'])
                        image = image.filter(unsharp)
                except (KeyError, ValueError):  # Value error if wrong type of image.
                    pass
            if name == 'dither':
                try:
                    if op['enable'] and op['type'] is not None:
                        if image.mode == 'RGBA':
                            pixel_data = image.load()
                            width, height = image.size
                            for y in range(height):
                                for x in range(width):
                                    if pixel_data[x, y][3] == 0:
                                        pixel_data[x, y] = (255, 255, 255, 255)
                        image = image.convert("1")
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
            ftt = [0] + [3 * (h[i + 1] - h[i]) / (w[i + 1] + w[i]) for i in range(0, N - 1)] + [0]
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
            r.extend(int(round(A[i] * (x - a) ** 3 + B[i] * (x - a) ** 2 + C[i] * (x - a) + D[i])) for x in range(a, b))
        for i in range(p[-1][0], 256):
            r.append(255)
        r.append(round(int(p[-1][1])))
        return r
