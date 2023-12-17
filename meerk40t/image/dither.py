"""
This function and the associated _DIFFUSION_MAPS taken from hitherdither. MIT License.
:copyright: 2016-2017 by hbldh <henrik.blidh@nedomkull.com>
https://github.com/hbldh/hitherdither

Suggestion to use Numba via Sophist https://github.com/meerk40t/meerk40t/issues/2332
referencing: https://www.youtube.com/watch?v=Ld_cz1JwRHk
"""

from PIL import Image

import numpy as np

try:
    from numba import njit
except ImportError:
    # Jit does not exist, add a dummy decorator and continue.
    def njit(*args, **kwargs):
        def inner(func):
            return func

        return inner


_DIFFUSION_MAPS = {
    "floyd-steinberg": (
        (1, 0, 7 / 16),
        (-1, 1, 3 / 16),
        (0, 1, 5 / 16),
        (1, 1, 1 / 16),
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


@njit(nogil=True)
def fast_dither(image, diff_map):
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


function_map = {
    "atkinson": atkinson,
    "floyd-steinberg": floyd_steinberg,
    "jarvis-judice-ninke": jarvis_judice_ninke,
    "stucki": stucki,
    "burkes": burkes,
    "sierra3": sierra3,
    "sierra2": sierra2,
    "sierra-2-4a": sierra_2_4a,
}


def dither(image, method="Floyd-Steinberg"):
    method = method.lower()
    dither_function = function_map.get(method)
    if not dither_function:
        raise NotImplementedError

    diff = image.convert("F")
    data = np.array(diff).astype(np.float32)
    dither_function(data)
    diff = Image.fromarray(data)
    return diff
