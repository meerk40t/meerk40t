from copy import copy
from math import ceil, floor


def actualize(image, matrix, step_level, inverted=False, crop=True):
    """
    Makes PIL image actual in that it manipulates the pixels to actually exist
    rather than simply apply the transform on the image to give the resulting image.
    Since our goal is to raster the images real pixels this is required.

    SVG matrices are defined as follows.
    [a c e]
    [b d f]

    Pil requires a, c, e, b, d, f accordingly.

    As of 0.7.2 this converts the image to "L" as part of the process.

    There is a small amount of slop at the edge of converted images sometimes, so it's essential
    to mark the image as inverted if black should be treated as empty pixels. The scaled down image
    cannot lose the edge pixels since they could be important, but also dim may not be be a multiple
    of step level which requires an introduced empty edge pixel to be added.

    @param image: image to be actualized
    @param matrix: current applied matrix of the image
    @param step_level: step level at which the actualization should occur
    @param inverted: should actualize treat black as empty rather than white
    @param crop: should actualize crop the empty edge values
    @return: actualized image, straight matrix
    """
    from PIL import Image
    assert(isinstance(image, Image.Image))
    try:
        # If transparency we paste 0 into the image where transparent.
        mask = image.getchannel("A").point(lambda e: 255 - e)
        image_copy = image.copy()  # Correct knock-on-effect.
        image_copy.paste(mask, None, mask)
        image = image_copy
    except ValueError:
        pass
    matrix = copy(matrix)  # Prevent Knock-on effect.
    if image.mode != "L":
        # All images must be greyscale
        image = image.convert("L")

    box = None
    if crop:
        try:
            # Get the bbox cutting off the white edges.
            if inverted:
                box = image.getbbox()
            else:
                box = image.point(lambda e: 255 - e).getbbox()
        except ValueError:
            pass

    if box is None:
        # If box is entirely white, or bbox caused value error.
        box = (0, 0, image.width, image.height)

    # Find the boundary points of the rotated box edges.
    boundary_points = [
        matrix.point_in_matrix_space([box[0], box[1]]),  # Top-left
        matrix.point_in_matrix_space([box[2], box[1]]),  # Top-right
        matrix.point_in_matrix_space([box[0], box[3]]),  # Bottom-left
        matrix.point_in_matrix_space([box[2], box[3]]),  # Bottom-right
    ]
    xs = [e[0] for e in boundary_points]
    ys = [e[1] for e in boundary_points]

    # bbox here is expanded matrix size of box.
    step_scale = 1 / float(step_level)

    bbox = min(xs), min(ys), max(xs), max(ys)

    element_width = ceil(bbox[2] * step_scale) - floor(bbox[0] * step_scale)
    element_height = ceil(bbox[3] * step_scale) - floor(bbox[1] * step_scale)
    tx = bbox[0]
    ty = bbox[1]
    matrix.post_translate(-tx, -ty)
    matrix.post_scale(step_scale, step_scale)
    try:
        matrix.inverse()
    except ZeroDivisionError:
        # Rare crash if matrix is malformed and cannot invert.
        matrix.reset()
        matrix.post_translate(-tx, -ty)
        matrix.post_scale(step_scale, step_scale)
    image = image.transform(
        (element_width, element_height),
        Image.AFFINE,
        (matrix.a, matrix.c, matrix.e, matrix.b, matrix.d, matrix.f),
        resample=Image.BICUBIC,
        fillcolor="black" if inverted else "white",
    )
    matrix.reset()
    box = None
    if crop:
        try:
            if inverted:
                box = image.getbbox()
            else:
                box = image.point(lambda e: 255 - e).getbbox()
        except ValueError:
            pass
        if box is not None:
            width = box[2] - box[0]
            height = box[3] - box[1]
            if width != element_width or height != element_height:
                image = image.crop(box)
                matrix.post_translate(box[0], box[1])
    # step level requires the new actualized matrix be scaled up.
    matrix.post_scale(step_level, step_level)
    matrix.post_translate(tx, ty)
    return image, matrix
