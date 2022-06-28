from copy import copy
from math import ceil, floor


def actualize(image, matrix, step_x, step_y, inverted=False, crop=True):
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
    cannot lose the edge pixels since they could be important, but also dim may not be a multiple
    of step level which requires an introduced empty edge pixel to be added.

    @param image: image to be actualized
    @param matrix: current applied matrix of the image
    @param step_x: step_x level at which the actualization should occur
    @param step_y: step_y level at which the actualization should occur
    @param inverted: should actualize treat black as empty rather than white
    @param crop: should actualize crop the empty edge values
    @return: actualized image, straight matrix
    """
    from PIL import Image

    assert step_x != 0
    assert step_y != 0
    assert isinstance(image, Image.Image)
    if "transparency" in image.info:
        image = image.convert("RGBA")
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
        # If box is entirely white, bbox caused value error, or crop not set.
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
    step_scale_x = 1 / float(step_x)
    step_scale_y = 1 / float(step_y)

    bbox = min(xs), min(ys), max(xs), max(ys)

    image_width = ceil(abs(bbox[2] * step_scale_x)) - floor(abs(bbox[0] * step_scale_x))
    image_height = ceil(abs(bbox[3] * step_scale_y)) - floor(
        abs(bbox[1] * step_scale_y)
    )
    tx = bbox[0]
    ty = bbox[1]
    matrix.post_translate(-tx, -ty)
    matrix.post_scale(step_scale_x, step_scale_y)
    if step_y < 0:
        matrix.post_translate(0, image_height)
    if step_x < 0:
        matrix.post_translate(image_width, 0)
    try:
        matrix.inverse()
    except ZeroDivisionError:
        # Rare crash if matrix is malformed and cannot invert.
        matrix.reset()
        matrix.post_translate(-tx, -ty)
        matrix.post_scale(step_scale_x, step_scale_y)
    image = image.transform(
        (image_width, image_height),
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
            if width != image_width or height != image_height:
                image = image.crop(box)
                matrix.post_translate(box[0], box[1])
    # step level requires the new actualized matrix be scaled up.
    if step_y < 0:
        matrix.post_translate(0, -image_height)
    if step_x < 0:
        matrix.post_translate(-image_width, 0)
    matrix.post_scale(step_x, step_y)
    matrix.post_translate(tx, ty)
    return image, matrix
