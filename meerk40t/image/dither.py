"""
This function and the associated _DIFFUSION_MAPS taken from hitherdither. MIT License.
:copyright: 2016-2017 by hbldh <henrik.blidh@nedomkull.com>
https://github.com/hbldh/hitherdither

Suggestion to use Numba via Sophist https://github.com/meerk40t/meerk40t/issues/2332
referencing: https://www.youtube.com/watch?v=Ld_cz1JwRHk
"""

import numpy as np
from PIL import Image

try:
    from numba import njit
except Exception as e:
    # Jit does not exist, add a dummy decorator and continue.
    # print (f"Encountered error: {e}")
    def njit(*args, **kwargs):
        def inner(func):
            return func

        return inner

"""
_DIFFUSION_MAPS = {
    "legacy-floyd-steinberg": (
        (1, 0, 7 / 16),
        (-1, 1, 3 / 16),
        (0, 1, 5 / 16),
        (1, 1, 1 / 16),
    ),
    "shiau-fan": (
        (1, 0, .5),
        (-2, 1, 1/8),
        (-1, 1, 1/8),
        (0, 1, 2/8),
    ),
    "shiau-fan-2": (
        (1, 0, 0.5),
        (-3, 1, 1/16),
        (-2, 1, 1/16),
        (1, 1, 2/16),
        (0, 1, 4/16),
    ),
    "atkinson": (
        (1, 0, 1 / 8),
        (2, 0, 1 / 8),
        (-1, 1, 1 / 8),
        (0, 1, 1 / 8),
        (1, 1, 1 / 8),
        (0, 2, 1 / 8),
    ),
    "jarvis-judice-ninke": (
        (1, 0, 7 / 48),
        (2, 0, 5 / 48),
        (-2, 1, 3 / 48),
        (-1, 1, 5 / 48),
        (0, 1, 7 / 48),
        (1, 1, 5 / 48),
        (2, 1, 3 / 48),
        (-2, 2, 1 / 48),
        (-1, 2, 3 / 48),
        (0, 2, 5 / 48),
        (1, 2, 3 / 48),
        (2, 2, 1 / 48),
    ),
    "stucki": (
        (1, 0, 8 / 42),
        (2, 0, 4 / 42),
        (-2, 1, 2 / 42),
        (-1, 1, 4 / 42),
        (0, 1, 8 / 42),
        (1, 1, 4 / 42),
        (2, 1, 2 / 42),
        (-2, 2, 1 / 42),
        (-1, 2, 2 / 42),
        (0, 2, 4 / 42),
        (1, 2, 2 / 42),
        (2, 2, 1 / 42),
    ),
    "burkes": (
        (1, 0, 8 / 32),
        (2, 0, 4 / 32),
        (-2, 1, 2 / 32),
        (-1, 1, 4 / 32),
        (0, 1, 8 / 32),
        (1, 1, 4 / 32),
        (2, 1, 2 / 32),
    ),
    "sierra3": (
        (1, 0, 5 / 32),
        (2, 0, 3 / 32),
        (-2, 1, 2 / 32),
        (-1, 1, 4 / 32),
        (0, 1, 5 / 32),
        (1, 1, 4 / 32),
        (2, 1, 2 / 32),
        (-1, 2, 2 / 32),
        (0, 2, 3 / 32),
        (1, 2, 2 / 32),
    ),
    "sierra2": (
        (1, 0, 4 / 16),
        (2, 0, 3 / 16),
        (-2, 1, 1 / 16),
        (-1, 1, 2 / 16),
        (0, 1, 3 / 16),
        (1, 1, 2 / 16),
        (2, 1, 1 / 16),
    ),
    "sierra-2-4a": (
        (1, 0, 2 / 4),
        (-1, 1, 1 / 4),
        (0, 1, 1 / 4),
    ),
}
"""

@njit("f4[:,:](f4[:,:])", nogil=True)
def floyd_steinberg(image):
    diff_map = (
        (1, 0, 7 / 16),
        (-1, 1, 3 / 16),
        (0, 1, 5 / 16),
        (1, 1, 1 / 16),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image


@njit("f4[:,:](f4[:,:])", nogil=True)
def atkinson(image):
    diff_map = (
        (1, 0, 1 / 8),
        (2, 0, 1 / 8),
        (-1, 1, 1 / 8),
        (0, 1, 1 / 8),
        (1, 1, 1 / 8),
        (0, 2, 1 / 8),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image


@njit("f4[:,:](f4[:,:])", nogil=True)
def jarvis_judice_ninke(image):
    diff_map = (
        (1, 0, 7 / 48),
        (2, 0, 5 / 48),
        (-2, 1, 3 / 48),
        (-1, 1, 5 / 48),
        (0, 1, 7 / 48),
        (1, 1, 5 / 48),
        (2, 1, 3 / 48),
        (-2, 2, 1 / 48),
        (-1, 2, 3 / 48),
        (0, 2, 5 / 48),
        (1, 2, 3 / 48),
        (2, 2, 1 / 48),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image


@njit("f4[:,:](f4[:,:])", nogil=True)
def stucki(image):
    diff_map = (
        (1, 0, 8 / 42),
        (2, 0, 4 / 42),
        (-2, 1, 2 / 42),
        (-1, 1, 4 / 42),
        (0, 1, 8 / 42),
        (1, 1, 4 / 42),
        (2, 1, 2 / 42),
        (-2, 2, 1 / 42),
        (-1, 2, 2 / 42),
        (0, 2, 4 / 42),
        (1, 2, 2 / 42),
        (2, 2, 1 / 42),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image


@njit("f4[:,:](f4[:,:])", nogil=True)
def burkes(image):
    diff_map = (
        (1, 0, 8 / 32),
        (2, 0, 4 / 32),
        (-2, 1, 2 / 32),
        (-1, 1, 4 / 32),
        (0, 1, 8 / 32),
        (1, 1, 4 / 32),
        (2, 1, 2 / 32),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image


@njit("f4[:,:](f4[:,:])", nogil=True)
def sierra3(image):
    diff_map = (
        (1, 0, 5 / 32),
        (2, 0, 3 / 32),
        (-2, 1, 2 / 32),
        (-1, 1, 4 / 32),
        (0, 1, 5 / 32),
        (1, 1, 4 / 32),
        (2, 1, 2 / 32),
        (-1, 2, 2 / 32),
        (0, 2, 3 / 32),
        (1, 2, 2 / 32),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image


@njit("f4[:,:](f4[:,:])", nogil=True)
def sierra2(image):
    diff_map = (
        (1, 0, 4 / 16),
        (2, 0, 3 / 16),
        (-2, 1, 1 / 16),
        (-1, 1, 2 / 16),
        (0, 1, 3 / 16),
        (1, 1, 2 / 16),
        (2, 1, 1 / 16),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image


@njit("f4[:,:](f4[:,:])", nogil=True)
def sierra_2_4a(image):
    diff_map = (
        (1, 0, 2 / 4),
        (-1, 1, 1 / 4),
        (0, 1, 1 / 4),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image

@njit("f4[:,:](f4[:,:])", nogil=True)
def shiau_fan(image):
    diff_map = (
        (1, 0, .5),
        (-2, 1, 1/8),
        (-1, 1, 1/8),
        (0, 1, 2/8),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image

@njit("f4[:,:](f4[:,:])", nogil=True)
def shiau_fan_2(image):
    diff_map = (
        (1, 0, 0.5),
        (-3, 1, 1/16),
        (-2, 1, 1/16),
        (1, 1, 2/16),
        (0, 1, 4/16),
    )
    width, height = image.shape
    for y in range(height):
        for x in range(width):
            pixel = image[x, y]
            image[x, y] = 0 if pixel <= 127 else 255
            error = pixel - image[x, y]
            for dx, dy, diffusion_coefficient in diff_map:
                xn, yn = x + dx, y + dy
                if (0 <= xn < width) and (0 <= yn < height):
                    image[xn, yn] += error * diffusion_coefficient
    return image

def bayer_dither(image):
    """
    4x4 variant
    bayer_matrix = np.array([
            [0, 128, 32, 160],
            [192, 64, 224, 96],
            [48, 176, 16, 144],
            [240, 112, 208, 80]
        ], dtype=np.uint8)
    """
    bayer_matrix = np.array([
        [0, 48, 12, 60, 3, 51, 15, 63],
        [32, 16, 44, 28, 35, 19, 47, 31],
        [8, 56, 4, 52, 11, 59, 7, 55],
        [40, 24, 36, 20, 43, 27, 39, 23],
        [2, 50, 14, 62, 1, 49, 13, 61],
        [34, 18, 46, 30, 33, 17, 45, 29],
        [10, 58, 6, 54, 9, 57, 5, 53],
        [42, 26, 38, 22, 41, 25, 37, 21]
        ], dtype=np.uint8)
    height, width = image.shape
    matrix_size = bayer_matrix.shape[0]

    # Repeat the Bayer matrix to match the image size
    tiled_bayer_matrix = np.tile(bayer_matrix, (height // matrix_size + 1, width // matrix_size + 1))
    tiled_bayer_matrix = tiled_bayer_matrix[:height, :width]

    # Apply Bayer matrix dithering
    return np.where(image > tiled_bayer_matrix, 255, 0)

def bayer_blue_dither(image):
    """
    http://cv.ulichney.com/papers/1993-void-cluster.pdf
    """
    blue_noise = np.random.randint(0, 256, (10, 10), dtype=np.uint8)
    dithered_image = bayer_dither(image)
    height, width = image.shape

    # Repeat the blue noise to match the image size
    tiled_blue_noise = np.tile(blue_noise, (height // blue_noise.shape[0] + 1, width // blue_noise.shape[1] + 1))
    tiled_blue_noise = tiled_blue_noise[:height, :width]

    # Add blue noise to the image
    noisy_image = dithered_image + tiled_blue_noise * np.random.uniform(-1.0, 1.0, image.shape)
    noisy_image = np.clip(noisy_image, 0, 255).astype(np.uint8)
    return noisy_image


function_map = {
    "atkinson": atkinson,
    "legacy-floyd-steinberg": floyd_steinberg,
    "jarvis-judice-ninke": jarvis_judice_ninke,
    "stucki": stucki,
    "burkes": burkes,
    "sierra3": sierra3,
    "sierra2": sierra2,
    "sierra-2-4a": sierra_2_4a,
    "shiau-fan": shiau_fan,
    "shiau-fan-2": shiau_fan_2,
    "bayer": bayer_dither,
    "bayer-blue": bayer_blue_dither,
}

def dither(image, method="Legacy-Floyd-Steinberg"):
    method = method.lower()
    dither_function = function_map.get(method)
    if not dither_function:
        raise NotImplementedError

    diff = image.convert("F")
    data = np.array(diff).astype(np.float32)
    dither_function(data)
    diff = Image.fromarray(data)
    return diff
