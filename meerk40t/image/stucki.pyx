import cython

import numpy as np
cimport numpy as np

cdef inline int clip(int value):
    return min(255, max(0, value))

@cython.boundscheck(False)  # Disable bounds checking for performance
@cython.wraparound(False)   # Disable negative indexing for performance 1    

def stucki_dither_cython(np.ndarray[np.uint8_t, ndim=2] image):
    cdef int height = image.shape[0]
    cdef int width = image.shape[1]
    cdef np.ndarray[np.uint8_t, ndim=2] dithered_image = np.zeros_like(image)

    cdef int x, y, old_pixel, new_pixel, error
    cdef int error8, error4, error2

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