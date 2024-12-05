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


_DIFFUSION_MAPS = {
    "legacy-floyd-steinberg": (
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


import meerk40t.image.stucki as cstucki
def c_stucki(data : np.ndarray):
    print ("Call c_stucki")
    diff = cstucki.stucki_dither_cython(data)
    print ("Return from c_stucki")
    return diff

def stucki_dither_cython( image : np.ndarray):
    height : int = image.shape[0]
    width : int = image.shape[1]
    dithered_image = np.zeros_like(image)
    def clip(value : int) -> int:
        return min(255, max(0, value))

    for y in range(height):
        for x in range(width):
            old_pixel = image[y, x]
            new_pixel = 255 if old_pixel > 127 else 0
            dithered_image[y, x] = new_pixel
            error = old_pixel - new_pixel

            error8 = error * 8 // 32
            error4 = error * 4 // 32
            error2 = error * 2 // 32

            if x + 1 < width:
                image[y, x + 1] = clip(image[y, x + 1] + error8)
            if x + 2 < width:
                image[y, x + 2] = clip(image[y, x + 2] + error4)
            if y + 1 < height:
                if x - 2 >= 0:
                    image[y + 1, x - 2] = clip(image[y + 1, x - 2] + error2)
                if x - 1 >= 0:
                    image[y + 1, x - 1] = clip(image[y + 1, x - 1] + error4)
                image[y + 1, x] = clip(image[y + 1, x] + error8)
                if x + 1 < width:
                    image[y + 1, x + 1] = clip(image[y + 1, x + 1] + error4)
                if x + 2 < width:
                    image[y + 1, x + 2] = clip(image[y + 1, x + 2] + error2)

    return dithered_image

function_map = {
    "cython": c_stucki,
    "cython2": stucki_dither_cython,
    "atkinson": atkinson,
    "legacy-floyd-steinberg": floyd_steinberg,
    "jarvis-judice-ninke": jarvis_judice_ninke,
    "stucki": stucki,
    "burkes": burkes,
    "sierra3": sierra3,
    "sierra2": sierra2,
    "sierra-2-4a": sierra_2_4a,
}


def dither(image, method="Legacy-Floyd-Steinberg"):
    method = method.lower()
    if method == "burkes":
        method = "cython"
    if method == "atkinson":
        method = "cython2"
    dither_function = function_map.get(method)
    if not dither_function:
        raise NotImplementedError
    from time import perf_counter
    t0 = perf_counter()
    diff = image.convert("F")
    if method=="cython":
        data = np.array(diff).astype(np.uint8)
    else:
        data = np.array(diff).astype(np.float32)

    try:
        dither_function(data)
    except Exception as e:
        print (f"Crashed with {e}")
    diff = Image.fromarray(data)
    t1 = perf_counter()
    print (f"Method {method} took {t1 -t0:.2f}sec")
    return diff
