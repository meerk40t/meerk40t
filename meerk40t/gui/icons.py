from wx import IMAGE_ALPHA_OPAQUE, Bitmap
from wx.lib.embeddedimage import PyEmbeddedImage as py_embedded_image

"""
icons serves as a central repository for icons and other assets. These are all processed as PyEmbeddedImages which is
extended from the wx.lib utility of the same name. We allow several additional modifications to these assets. For
example we allow resizing and inverting this allows us to easily reuse the icons and to use the icons for dark themed
guis. We permit rotation of the icons, so as to permit reusing these icons and coloring the icons to match a particular
colored object, for example the icons in the tree for operations using color specific matching.

----
The icons are from Icon8 and typically IOS Glyph, IOS or Windows Metro in style.

https://icons8.com/icons

Find the desired icon and download in 50x50. We use the free license.

Put the icon file in the Pycharm working directory.
Using Local Terminal, with wxPython installed.

img2py -a icons8-icon-name-50.png icons.py

Paste the icon8_icon_name PyEmbeddedImage() block into icons.py
"""

DARKMODE = False

STD_ICON_SIZE = 50

_MIN_ICON_SIZE = 0
_GLOBAL_FACTOR = 1.0


def set_icon_appearance(factor, min_size):
    global _MIN_ICON_SIZE
    global _GLOBAL_FACTOR
    _MIN_ICON_SIZE = min_size
    _GLOBAL_FACTOR = factor


def get_default_icon_size():
    return int(_GLOBAL_FACTOR * STD_ICON_SIZE)


def get_default_scale_factor():
    return _GLOBAL_FACTOR


class PyEmbeddedImage(py_embedded_image):
    def __init__(self, data):
        super().__init__(data)

    def GetBitmap(
        self,
        use_theme=True,
        resize=None,
        color=None,
        rotate=None,
        noadjustment=False,
        keepalpha=False,
    ):
        """
        Assumes greyscale icon black on transparent background using alpha for shading
        Ready for Dark Theme
        If color is provided, the black is changed to this
        If color is close to background, alpha is removed and negative background added
        so, we don't get black icon on black background or white on white background.

        @param use_theme:
        @param resize:
        @param color:
        @param rotate:
        @param noadjustment: Disables size adjustment based on global factor
        @param keepalpha: maintain the alpha from the original asset
        @return:
        """

        image = py_embedded_image.GetImage(self)
        if not noadjustment and _GLOBAL_FACTOR != 1.0:
            oldresize = resize
            wd, ht = image.GetSize()
            if resize is not None:
                if isinstance(resize, int) or isinstance(resize, float):
                    resize *= _GLOBAL_FACTOR
                    if 0 < _MIN_ICON_SIZE < oldresize:
                        if resize < _MIN_ICON_SIZE:
                            resize = _MIN_ICON_SIZE
                elif isinstance(resize, tuple):  # (tuple wd ht)
                    resize = [oldresize[0], oldresize[1]]
                    for i in range(2):
                        resize[i] *= _GLOBAL_FACTOR
                        if 0 < _MIN_ICON_SIZE < oldresize[i]:
                            if resize[i] < _MIN_ICON_SIZE:
                                resize[i] = _MIN_ICON_SIZE
            else:
                resize = [wd, ht]
                oldresize = (wd, ht)
                for i in range(2):
                    resize[i] *= _GLOBAL_FACTOR
                    if 0 < _MIN_ICON_SIZE < oldresize[i]:
                        if resize[i] < _MIN_ICON_SIZE:
                            resize[i] = _MIN_ICON_SIZE
            # print ("Will adjust from %s to %s (was: %s)" % ((wd, ht), resize, oldresize))

        if resize is not None:
            if isinstance(resize, int) or isinstance(resize, float):
                image = image.Scale(int(resize), int(resize))
            else:
                image = image.Scale(int(resize[0]), int(resize[1]))
        if rotate is not None:
            if rotate == 1:
                image = image.Rotate90()
            elif rotate == 2:
                image = image.Rotate180()
            elif rotate == 3:
                image = image.Rotate90(False)
        if (
            color is not None
            and color.red is not None
            and color.green is not None
            and color.blue is not None
        ):
            image.Replace(0, 0, 0, color.red, color.green, color.blue)
            if DARKMODE and use_theme:
                reverse = color.distance_to("black") <= 200
                black_bg = False
            else:
                reverse = color.distance_to("white") <= 200
                black_bg = True
            if reverse and not keepalpha:
                self.RemoveAlpha(image, black_bg=black_bg)
        elif DARKMODE and use_theme:
            image.Replace(0, 0, 0, 255, 255, 255)
        return Bitmap(image)

    def RemoveAlpha(self, image, black_bg=False):
        if not image.HasAlpha():
            return
        bg_rgb = 0 if black_bg else 255
        for x in range(image.GetWidth()):
            for y in range(image.GetHeight()):
                a = image.GetAlpha(x, y)
                bg = int((255 - a) * bg_rgb / 255)
                r = int(image.GetRed(x, y) * a / 255) + bg
                g = int(image.GetGreen(x, y) * a / 255) + bg
                b = int(image.GetBlue(x, y) * a / 255) + bg
                image.SetRGB(x, y, r, g, b)
                image.SetAlpha(x, y, IMAGE_ALPHA_OPAQUE)
        image.ClearAlpha()


icons8_add_file_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAALdSURBVGhD7Zq5qhRBFIYH10BETFxQ"
    b"UUEMBCMFF0xMFBNBcF8QDBTEB/ANTAVxx9DtGcw0ckP0BUTcMFFQEVxQ/w/mwKHt7ntmqqrn"
    b"Cv3DF3RNVU39XVOnTtW9g169emXRJrEvM+tE57op/mTmi9gmOlUJI9C5GW/kvXiSwHcxMTPe"
    b"yDkKEvRKeCPQmZnSRqATM6WMnBc/3HNxM6WMMOi9ojMzJY2gzsyUNoI6MVPKyGfx0fFT2GeA"
    b"GbKKbCplJALfnU29kRqtFxum4IKY9kYiOit6I23qjYyp3shU6o2Mqf/SyFyxS1wVnCDfiV/C"
    b"vu+F2C5miGSVMDJLnBQM3Ppu46U4LpIM5TayQjwVfqBR7otlYizlNLJRcIHhB0eWe0scFlvE"
    b"GrFVHBG3xVfh69OeVGdk5TKyXHwQ1tdvcUksEm1aIi4L6lvb12K1GEk5jLAmngnr55vYL0bR"
    b"AUE76+OBGGnN5DBySlgfvFkGVdU8cc/Bc1UHhZ+ZMyKsVCOEWB+dLoo6LRBWB3iu0xVhdTjf"
    b"MNshpRphn7D2LOymNRE1slj4ALBbhJRqhM3O2hOdmhQ1gu4Iq9c0w/8o1Qg7trUnpJrmi4WO"
    b"lcLqAc/+c+qbjgmrRxAJKdWI3zc2UzAUUcfKI1DfxH5j5YT0kFKN+Bv4tRQMlWKEfqyc+7CQ"
    b"puOMsPNb+VsKIsq5Ro5SMFSuNfKYgohSjZCGWHtypyaNErXuCqtH/yGlGtkhrD3xn32gTlEj"
    b"S4XfR+g/JG9knD+9PRfWHpreYNTIdWF1SB7niJC8kRyQK5EzVRXJtQ4Jn2udEGHlNgJksXWJ"
    b"Y5sw4bPfh2KmCCvXPwywq/NTsIHwZjln8JtvE59fE34mSEI530xMnP68GWDhEoUIzewPdkIk"
    b"xFJePSFigsvuiWuVeCT84KLQbqIzURVniNOien5v4o1gYWe5Fiqh2WKPuCHIYj8J7rVIO3j7"
    b"hOqdoiXEDgZ/AYB+bilw1gi8AAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_comments_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAEcSURBVGhD7Zm7DcIwFEWzBzOwARvQ"
    b"0LAKtJSUtIxAzwAMQEXJAkhUbADvFpaiyI7jzzN2dI90msRx3pH4REpHCCGEEDtL8Vy5mNHL"
    b"WvxWLmb0MsuQt3isRMwSHfLAgUrALAxhiAJqITfxnlns6UIt5COadbnEni4YAsdCNuI2s9jT"
    b"hVpIaRjiCzmItkeJFLGnC7UQ/mqN+JeQ2Xy0SsMQX0jKH+JKDEUtJOXLfhVDYQgcC0l5jD+J"
    b"oaiFlIYhDFEiKeQl7iNciC5wznaNT8wSHRLrU7TF4BjO2a4JsVgIHMbkioCTQlJeK1zE/g1N"
    b"jC0Ca217THHSa4VUdmJ/YAQMI7CmCYYxfZuJMNhimosw9GOajTAgoPkIQtqm634PwFqxOUO9"
    b"7wAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_connected_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAKaSURBVGhD7ZjLrkxBFIabEIIEcyaI"
    b"4BnELSRuMWQk4QGEiaEQnsCEEQ+AgYmIRI7BSZi4DzwGIi4Dcfk+rGRlp7vP3rprdw/qS744"
    b"e+tOrb+7q2rtGlQqlUqlUplfVuEd3P3nao44iDdxEV/jY7yGO7GJIR7iL/yEcxFmOz5Dixrm"
    b"D7yN61ByiPAuzpR9+B5zUaN8g5uwGcLr1dgrK3H93z8Hh/ELRkE/8T6exRN4AV9iLvpr43pm"
    b"IfwJvMBT+A2jIAMdxSbL8Arm4sOZhhhWkCH8iY3jIub3+M1sxl4xxHK8hbmYKOgQtqEZ5i2u"
    b"xV6Ib8IQw8K8w43YlmYYV7PiNH9Oo8I4Z7qEyXPGpXkHFsXVySJz0YZY8e/ffL9LGBeA5xjv"
    b"vYTFcXXKBes0wrg0x/tcvYriPpGX2OykYY5jvMe9phgup3mzc3VyYse1ThLmDMbr7cmKsA0/"
    b"YgxkIJdYi5vWnLEDiNde90YJnmIM8hnzZjeNMHYAtjPxuv04dfzkYwAHO4JNJgnjh+KHE/+/"
    b"iEW4gTHIPW+M4H/C+LyS590H9GdchCcYA532xhi6hHGhyJ2vgfZgMV5hDHbMG0vQJUxoiANY"
    b"lEcYA573Rgu6hjmJxbmKMaBthO1EG7rOmQ1YlF1oIxeD2uC1pW0YG1HvFcfWOhdj690Ww4zr"
    b"AHoLIWvQh55cTNsw7kPN53KNML2FCLbid8zFLBVmL+Z9ItvrNxEMO3cKL+OwBcClOu/YBvIR"
    b"wDkzNyGa34zFnUN7Jo9+bABz75T3CVenuQjh9Rb0cC3fH6WHdUV37DZ4oJyLMkScO3nc6YTN"
    b"S3NTG8BivVMXPEj2QNmicoiMBwU+Yz9AN8wF9HmiSCs+CYZxcvZ+AlipVCqVSqUVg8FvvyiE"
    b"Su2rldYAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_down = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAD7SURBVGhD7Y9JCgIxFAV77bTUe7h2"
    b"PIIX0a2H8SyC0xH0IA4LN+r7yoMgjbZ00ibwCgqSQH5SmRBCCCGEEEKI6pjA6WsZnDpcwM5z"
    b"5xGLuMIbnNlBQCxiBe/wAL3FMMIGmyFj3Ai6h21YmjG8QHd4iBiLWEP3HXMJa9ALIxgypgGD"
    b"R5AhDBFTaQTxHWMRG+jOM4NGEF8xTfi3CDKAZWKiiCAWc4buR4rEWMQWuvfMv0SQX2OijCB9"
    b"WCSmBaONIN9ikoggFnOC7kctZg53zhmNMoLkxeQZdQTpwU8xSUQQiznCpCPIe0ySEYQxSUeQ"
    b"Lkw+QgghhBBCJE+WPQBgjKllZBue5gAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_left = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADASURBVGhD7c+5DcJAAERRx1wh9EHM"
    b"WQKNQEox1ILEVQIUwhGQAH9lnKy0sXfs+dKTJp3COeecE2yJVTl1W+CFN2TPzBFOfP8kz8Qn"
    b"gg/WkCl1YgOZZvCJHAonnpA+MYVP5FBjTjwgfWICn8ihcOIOn6i7MeITwRZSdbBHfOSCAaRK"
    b"nTmjUWf6kMpnci115oRGnelBqlacOaJRZ7qQqhVnDvCZOkud2UGu+MwNI0hWnblC9kRVODMs"
    b"p3POOVd3RfEDYnipZR7hKKAAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_right = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADYSURBVGhD7ZHJCQJREAUHvbkdNQUD"
    b"8OgagoloQmbhXXALQQNxOYigVjszoDBzUobpzysofv++FR0JIYQQP1BN3n/Rxife3z+ndPCA"
    b"K6zZwiMWcUS7huk2ZoFphOuYOq5RMWXDYjaomLLRwKBitqiYstHEoGJ2qJiyEVRMC4OK2ePf"
    b"YirJWzQnXMbjFz3sxqMP5vjAz2tYXB/dEGzEGRVRNHkRA3RDVsQFFVE0QUcM0Q1ZEVdURNHk"
    b"RYzQDTN0H2FM8YauI1LSGIsY28IzFjOJRyGEEMILUfQCpm2nw/NYYCkAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_home_filled_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAHeSURBVGhD7dk9SxxRGMXxJUGSqBhE"
    b"LGwUVLSxkFjEIvoFtDGVtVYRxNQpAkkVrCwTsUlAzDdIpY2lghAiaGMQBUsJgSiKJv8DzjLM"
    b"Pjp3ZncmV7gHfrhv83KQee6wWwlxyxh2sYo2vXAfs4AL/L2xjyHcm7RiDVGBuN+YhvcZwA9Y"
    b"JeKW0IR49Lzd0IJSM4VfsE7csokuRJmA9TldX6XkIT7gGtaJ3OUEGgjKY6wg+ZlSinRiHcmD"
    b"Z3GJ14gyizNE7xde5DmOED+penyFBoUygp/Q64UWeYVzJE+mXlpzBqF04BsKKfIEn2GdRKNo"
    b"YLyE8gDRNdSw9GIH1sEbTYNjERokDY1G4ymsgxZpAxoodUf/2ne4gnWgMhxjFLkTXWzWzsum"
    b"wTKHzHmGA1g7/Z++oBlOmUF8QfKNBk4fbs0jLMPa2DcaPJOoSTe2YG3kK43o99BAquYQejP6"
    b"6ztNMt2j6fEbVKO7Tq3YPUhu5CPdtoxD64zWuJo8hbWhb1Lvv0KRkoUivglFfFNokT/YzmAP"
    b"1n5cFFrkO7LkBaz9uAhFXIQiOYQiLkKRHEIRF6FIDqGIi1Akh1DERSiSQ2oRfdOd52dmKbOI"
    b"vkxMzTw+5fAWWdIPaz9pPmIYISHFp1L5B9V7aqEmmt6rAAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_disconnected_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAMOSURBVGhD7ZlNqw9RHMf/QhQKb4Cw"
    b"s7pRVh4SEeXhFXhcWJPssLAkL4CFlLhuNxJRHha8EHZuoTxbie+HfvXrdGb+Z2ZOM2cx3/rU"
    b"nfnPw+9zZ+acM2cmY8aMGVNSlosbYv2/pYKyTVwR8+KZuCVOi7UiDBJPxR/xVhQhs1G8EBQV"
    b"44u4IBYJ4iUMrsyg2S4+CV9UFQ/EKhFKsIxcr1kiFv//c7Jf/BC+qJfivDgjrosF4X//ECwP"
    b"JjEn7ouD4pewghA6LMJwBdjeF28MKhErCIldoipcwdvC78PtiGTvWSHeCF8MILFXTEtM5qGw"
    b"BqDXrBShzCvB1UpJTIbWbJDEZHgGmsjMCtv3s1gjBgkyr0VbGfZ/L2zfY2KwbBa/RVuZa8L2"
    b"G6wzXCcYVngJI1XmpLB9HrGi7zAmCiXeBcspMueEbX+PFX0mJnFRtHlmGAHYtpdZkSOckH6i"
    b"LqtFTMLSROao8NttEZ3DieixaVIppi785+zkXsKSIrNPfBf2O8OUzjEJO2iqTEzCwv5VzwwS"
    b"fnzGAHKD6Bw6J07iT5oiU5dLwh/PYAQQDjJ3iGw5IPwJoa1MKBH2MwYSu0W2cDAOGjtZU5lQ"
    b"goaBTjN8ZoB/XrZwWb3ET8Hl9ydMlYlJ0GkS9uc4/neey1hr1jibxEdhB0Zoj+DgbZ4Z35oh"
    b"EU4khDLZRJ4LOyhNoX8p6iITk7CYTDaJrcIXeUSEaStDp1kXOt0sEsTfBkzhVKWtTG/xHeBZ"
    b"VtSkaJnHwoo6wYopKVbmprCCrrIiIUXK8FppxTB5Nm3UaylOhgll5mKtGJ4ZxlwpKU6GKRhf"
    b"zB3RRKbtCCB7mBRjQtkXw+smRU4LI4DY+AyZ1Ns0a5hL+iZ8MdxmS0VVdoqqQWa2HrtJlolw"
    b"at8XFLtNDgn/ZocQo1i2L0bia7DM5BlN8ynBbEf4TCBh7xMI9C4R+1LEMi1Z+MxUwaiZjzuD"
    b"hhk9XxQS9n2CBoDWjLlYv42H74JZ3rG7xs9LeQkfrs5xgfQTcVcw0JwRRQUZiuz9S9GYMWPG"
    b"VGQy+Qs7CKtFP8P3cgAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_gas_industry_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAVlSURBVGhD7Zl3yIVTHMdfe0cie0XI"
    b"yN6SkWQkW0b+IFvJLpFNQsmKJCs7QoSUnZA9IitbSPaen8+5z6/3eU/n3vd93ee5977lW5/u"
    b"8zu/Z5zzPGf8fueODVCLwDXwHWxpwUzTHHAcfAP/VBwAM0qrwfMQDfi1+t0YZoRmgWPhF7Di"
    b"H8EecFNlrwkjr/nhLoivcB0sCOpqsGzzZI2wloWXwMo6JnaHuk4EfUcma0Rlv/8crOgbsDLk"
    b"2hT0P5CsEdRW8CNYyXtgAShpNvgM/oBSQ4eqreEnsBEOZivbS+eA596QrBGRs8+3YMVc7CZr"
    b"hHJh/B78KqtaMGwtBR9DvF2n3JJcEHOdBV73GHS7biCyck+BlXka5oSS9gNDkiuTNS6n40/A"
    b"6w+1YFg6H6yEX2QxCzL5li8AzxEngFw7gz675tIWDFrrwp/wG6xnQSYbcRVEI+RcKOk20P8g"
    b"DLSLOZgjdjrDgoLOA/2/g93O432hpEXhC/CcgywYlOzzPvRtKI2LvUC/X2xPcGxo94qtjME8"
    b"x5nMCaR1zQpvgg/d24JMy0GE6kdYgBwb2oYuvXQneJ5xWevaFXyY4UepP98L+m9JVkdPgmUR"
    b"NHaTDf0Z/oaNLGhTEdEenqyJ2gT0fQ32+1A0ZN5kdeSCOHvncILOBM91XLWmhcCkSEpx1MNg"
    b"JU5K1riiIUsmqxNY+uavTdZE2VjjMM9vLRV24PqAh5I1USuCXcLBai5SV3zF9cGv8FZlvwcl"
    b"nQL6692zUV0EPsCsL5dfQV9poF4G+g6GXapjMc6qd7eQYyVeytwWNK0nwAoY6ebyK+lzGs3l"
    b"JoM+Fz7jsWiIbAslPQv6S8/qW5+CNy+FI5FMlcIMx4ZvX3zLvu3rwfMvh5IuBv3HJ6thxSZC"
    b"Pu3OB5br76YIQ+QdWKE6/gpKi6pBpP4rktWg5gFvbHCXawnQ52zTTatAbAM5+NVzoG3gmMs8"
    b"X58voFE56LzxD8maqGiI2z29ZGhj7HVgsjobdl5nRpkrGlLy9S3nfm+ezyR2Dcvt/5OpnmAt"
    b"A44XX04+ex0G3tOx0rgi4nUXJJeN0DdXsqauWCzz7uUkYPkxyWpYMZOYouaKQNJFbzo6Hbzu"
    b"7GSNKxbNDZLVsDYEb256mnevmE4PSdbUFdHCrcnqyKTNMme0UjzWiCJHPzlZ47IBlt+RrKnL"
    b"BdHr7k9WR7FoGkm0JgO+SHHroXbEWg7c6YwTcxorHdPs2uD9nd1WsqBNxebal7C6BZUeB8ud"
    b"ZqeqS8BrTgXXqpcru5XZKpc5e2R9bvNsD2p/sOyZZE0up+3I1deBm6vj98GUYSCyEvH3gF3h"
    b"QvDh71ZlO8Fk2gc89xWI/0zcdl0LBq4TwGDQSvh2I2p9HXptnbowxpQd17sWbQNDk7sjsbDV"
    b"ORq6yRdQP9fu1MqaMV0ZEbsxEV9EHD/uuuSyTJ/nOPs54POsciTkguaYcSbqJtchN/cij/9f"
    b"/0UueruBYYUsD8r4KsqC2C10i6hebiocGeYWUPcZurtNpBz0Ub4dmLw1IkMQp9no//IaLAx5"
    b"uRjKuOvoap/7DEfWyMoC15LNsjL5APreSnVwug36F7iteR948w/BHQ+Pnf9vh9iEeBWczTw2"
    b"q9T3SGU7w/nXtMcGhnWf996xOjbj1Bfpg+OuL7nV6Y0izY3KWwl3HD22USoqrx0ZoI1SUXnX"
    b"DycCj22UCt8LEDv5NkpFw/rOFvOGLA7addxQUObmue9FUJEG1HkUVKk73Q2qtYYoN+T8Iydw"
    b"ElCuJ6dB3bcDKHMLE6i6z7+0lRGz/4DVfU4UqvGGmLM76AfNpdBIQ1x1vdGwuRH61lFQ/+yD"
    b"xo06k64eGhv7Fz7x+0gwmZssAAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_laser_beam_52 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADQAAAA0CAYAAADFeBvrAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"0UlEQVRoge2av2sUQRTHP3cXA5IEtNPEQoOggmBh0AQLlSAo/gsxWqmNCsbGRgRFI3aChaAQ"
    b"vM4QG8HKOiGFRP0DJCbxBzGaJhhRvLV4u2T27cwkuZu9u+K+MHA3783M9zu78+bN3BXIH5H6"
    b"XshzsGKenTcCLUHNjpagZkdLULOjJajZ0RLU7GgmQV1AGXgLXGgsFT8iVVwYM3wqwN7cmVWJ"
    b"jQg6iogw/Y7UhV0VWE9QAZhSPu+BUr0IbhbrCTpn8TlVN3YOFIA+YL/F5hPUASwo+0R+NDeO"
    b"Z6wt5qvK5hN0R9lWgd48CLYDD4HXwEWgzePbRXpB/1J2n6BVZbtXK3EXbqqBPgCDDt8i8Ak3"
    b"aZ8gs/4z0BmAuxVPLEQi4CX2V2KY2gUNB+JuxSHgp4VMBPwG7pOezQIwvQHSLts06dugIvIq"
    b"B8VOZPf+ZyEVAV+A8waRftbWko20S1Albkvc1zDyCleAp+Rw7XUEmLQQM2d3IPYtO0j7BJXj"
    b"z/2kn3JSDoWTsoYCMER2zzBzrzIifsVC2iVoJW5TJpv6JP3mEsYTdCB7hw63SVkBZlUbn6DZ"
    b"uI2tr1/A5fAS7NgFPMc+q9VGObO8AvbkxN2L48CMIrOsfHyClpVtJu6zoSgikekbQuqWYWsn"
    b"K6jdsN+O634A1wiUYZ/Fvdg3WyrADqPvUYvPqGHfGWjcCJgHzhB/CNXpdzVZXyw+X5XPUsDx"
    b"50LfKehXRq8ZkI3a16YmFJFseiFQf9uR1yhB2eJj1nUD2wKNPY9oqRmluKNF5IlcN2ztyJr5"
    b"HJdR0kHhRtxmEbhEExy7bWF7EZn59dBDdv00LGzvBsZxL84Z/KJ6gHee9uPxGHXBNSQtsRFJ"
    b"Up8k4o2QFtaNvGbJk5nFnfqsImlWR55i9uFOIs3kVNuXyWYFyQT4ktMICVhD5PTreZ9lwGnW"
    b"zjNlZVu0+Ou6JOoNYD8+JGWSHC4fC8ihq4IcwoaxH/CScslC7KL6rg9457FvyBGyh42R3hqC"
    b"oJP0Rb8+gkfIoi9ZSJXIRkZ9BO9Ejvm/HcKWgIOhRZnQlyQRcCK26XqQ0KzrbZckvcjFjE3U"
    b"o/AyBJ3IpqnDbgKbIIAXqv6jZ4xB5CrN9B8JQz+Le2qgVdJ7iEvQbtLh/y+w1TNOG7L+XgMP"
    b"gC0hyGv0kj2O31U+LkEge1oSSB7nQXCzmCC7Z+jbT58gkL3tMDn/S2sjOEmW7JDFbz1BTYES"
    b"8qOUSXQK+yybB8i5ehHcLI6R3RyPOnzPIKLmgNN1YVcFDpDOCsYaysZAtQeqJSQ96QbeAFeA"
    b"P6FI1YL/vgFTqCh5LwAAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_padlock_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAFqSURBVGhD7dXPKgVhGMfxIcUdKG5A"
    b"hJKyscFCFFaW1jYnW25ALsEV2CALC7KykLKwslK2SllIiUL+fH/lqdN0GF7nnT+n51uf0mSa"
    b"+XXmzEk8zyusTgxjGpPoRxcqUTsWcIAnfKQ8Yg/zKG0DOEX65r9zAn1KpWoOD0jfrD6BS1yh"
    b"0Sd0jxmUIj3/z6i/wV1MoAOW/p6CHq132P/q3HEUWg/uYDelv2eRlV4A9efdohuFtQ27GT0m"
    b"Q/htI9CjZ+dvopD68Aa7kSX8tWXY+a/oRe61Qd+PHZzpQED63uhFYGNqKDT9foS2DhuyrwNV"
    b"TT+ONuRCB6raKGyI3l6VbRA2RG++yuZDylauQ1agX/EYjmBDXr6O1dO1m9YW7GJ507WbVksO"
    b"OcZqZIeIPmRDByK3Bh/yUz4kMB+SlQ8JzIdk5UMC8yFZ+ZDAfEhWPiQwH5JVSw65wXlk14g+"
    b"JG8+pFFjWCyIru153r9Kkk8J85i7zVovlgAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_opened_folder_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAK9SURBVGhD7Zk7aBRRFIYXLIKCEQux"
    b"ExEhYhcFCxEFUSsxCJFgAqJ2goWIdiJaiIrgI50kjRoLEdJpumApsfIBFpKg4AvxBYqF7/87"
    b"zFnuzowxu8p41P3gY+bc7C7nz+7cO49amzZtfspsOShfy29N+FSul2E4LWnsiyTMTHwrec87"
    b"uVSG4LmkqeVWzZwLkvfdlLMY+NPQDDbLPPlQ8t6jcn4Fdsof0moQWCc/S/+MKnwk+2QBf0Gr"
    b"9MoHsuxY+t36sck/b5Vs4FeDVM0xSb+nrEr424L0S/q9bFXCfxFkjlwSzH2Sfq/KBsqCMM1d"
    b"kZ+k/z2iL+QOafhgynnJGCv3ZFCZhr/K+gyWD8Iq/VLybSxkIDDHJb0zkxWCLJPU96yKzRFJ"
    b"r4co8kFYNakLs0JARiW9bqHIB/Gv66BVsZmS9LqIIh/kuqTeZFVcOGnlYH9llcgHeSKpox/o"
    b"ayV9jlsl0iALJPvPrIrNXkmvZ6wSaZCNkv0xq2IzLOl1p1UiDXJAsn/CqtjckvTabZVIg1yS"
    b"7G+3Ki4s2h/kR9nBAKRB7kj2m71+rxr6o8/bVmV4EJJxWkLSEDcTpoFfDD1ftCrDg6zIthMy"
    b"Oiclve63KsOD7Mq2QzI6zKr0usGqDA9yNtsyP0eHdY5eWffqeJAb2XaNjAxnHPT52KoED/JG"
    b"cu4yV0bGF+1rViV4EOTKKzqcldOrXUylpEE4v4/OiKTXwt3GNMhhBoLDlSu9dlmVkAbpYSAw"
    b"vmi/l4VFOw2ymIHArJT0yaOMAh6CWSs6uyW9cruqgAdhHYmOL9p7rMrhQc5ZFRtftFdblcOD"
    b"8LVFh58/zzpLF20PwoEUGSYi+uShUikk5AU8po7MVkmfhbvwzl3JC7gbsS2oA5LrJPrksUIp"
    b"m2XVDzRb9b6c9skudyK46mJ+jip3eKKfmbf516jVvgPWjL2OHf8X/wAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8up = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADySURBVGhD7c9JCsJAEIXhrJ2Weg/X"
    b"jkfwIrr1MJ5FcDqCHsRh4UZ9jRaEkEokdsdqeB88aGrR8CdERERERBY0sP77GS8XscbO2MAd"
    b"YiQRz8+ijMlGRBmjRcgumPmYsgiZixliJmkRB2yJPVI3N5MxWsQe62DOAsvGXDEzMd9ECLMx"
    b"RRFtLI8WM8L+okqEMBOjReywsgiRF3PDaovxESG0mDEWVFFEC6ui9hgtYotVjRC1xYSMEFrM"
    b"BPOiKKKJ+aTFTLGfdbEjlv58g/mOENmYOzbDvOhhJyx0hJAYrxHCxayw0BFijnmPICIiIiIi"
    b"olxJ8gJfK6lldYiKtAAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_usb_connector_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAMvSURBVGhD7ZlLqE1RGMeP9yuKJPKM"
    b"DBSllJC8MiIkMUAZkFeSIhOPDKSUgQETjJSBMvEoEga4pRBFCil5JEKSV96/37l71b7bOfse"
    b"g3Pu2tx//Wrv7+zT/v5nf3utb61Tatd/qO0wuvmwuBoGH+FE+azAOga/4CdMMVBETQINaESa"
    b"oAMUSiZ8DTSwF54nx4ugUFoOJv4EesKq5PwBdIFCyMSfgokvM4A6wV0wtsFAEbQLTPgWDIGR"
    b"CevB+CvoA1FrKDjcmnAeeyBqHYS34K/+CEKJfU7OAzehNxRG40AjV8pnLdUdQtlVYiBEozwj"
    b"UyGUWiXOQDSqxUi27F5AIY1kP5sLDTUyCPo2H1ZV1EZmgTO0N7OXugijoJKiNTIdQiP4Gj4k"
    b"xy9hAGRVi5HrkB6tVkLdjdwBb7IDbAxtR04lsQOQVS1GqlE3I73AGzhzdzSQaCIYd5LLKs/I"
    b"eLiR8BC87l0qth/qIpP/BN+hv4FE88EkzpfPWirPSFoNH6mOgze8DLNhCdiqG7MpzKpWI/Og"
    b"oUYGw33wpmlOQ2fIqhYjPt1z4HV1K6dKcu7YDd7YUWsFVDKh8oxYquvAJtNrHPmGQ0Nlu+7N"
    b"Las8VTPiet7Bwc/EJ9pwE6obOHr54lvf1ZQ1YhkdgR9g3N4q7/sNUSgvJ0jnkB6QVTDSBOky"
    b"cvRzJVnpOw2XE+ImsHs1uXswAdIKRtJYRtVamjbVWLgNJvkVtoGbDSptJIoyak2+M+5fhdq3"
    b"lPzVgxFbmyjKqFZNg8dg8u9hX3Lc2oQYpdzqOQoaCBTSSNBieAOFN6Imwz9hZAZoxFm8UC97"
    b"0Exw5RfeEXG+OQT9oBBaC2E57I7jBfAvhm9JzFFtBEQt3wn7L9kC6a7Yv+EugWZ8WulVZnQ6"
    b"Cya6s3z2p1zjh2XtQgMxypfZFuUL5G1QbwSNHC6fRSjr3gT9xfPkQOB1ldb4UcjRyARt1fPq"
    b"fyl4nev/aGUrb5J5Xa4bDF5jiUWr1WCS/os7xkBGW8HPbV1a2zduU7kOOQkm6yrQCXANbIar"
    b"YNyheQFEr67g0jdMgGmewRwolNyQ9kloynWJ3XAh+612/b1Kpd96WyDV7qTTNwAAAABJRU5E"
    b"rkJggg=="
)

# ----------------------------------------------------------------------
icon_meerk40t = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD/gAIDAAAAA3NCSVQICAjb4U/gAAAgAElE"
    b"QVR4nGy8Wawk6XUmdv4l9oiM3Je7L9W31q7u6m51s7mIpJqkRGqGoiBpJHkkeTDSAB6PBvCD"
    b"AdlPnmcvAwMW4AfDDza8YCCNOCPKlEVSHKopsnrvWrq6uqpu3f3mvbkvsUf8ix/+qmSxx/lQ"
    b"yJuVGcv5v/Od75z/nEDr6+sYYwDgnEsp1XshBEKIUooQ4pxzzgEAISQR5EgihDQmdaoB44AR"
    b"lxJpRAghAIgEhBBCSH0OgInAOiYsLzARiGDOC4qJAJlhCQAak0iCoFRgJEAKITSEJRfqIEII"
    b"dV71rxBCCKHruhCiKApKqUTABBANC5lTAD1DGAjW9DBNbNtOi1RKpC5bIoEwY0Jgjp98KKU6"
    b"IMYYY8wYk1IihAgh6lyMMWUHAJBSAgApl8vqZ+pv9ZJSEkLUe4SQsiAASJCUUiQBpAQhAWMJ"
    b"gAiWAAghgjFGCANCT48uQSKEEEGSc4RBIiSRxIgIQIAJwqBLTAAJLBHCUgICoITA0ytRB1lc"
    b"rroT9V7dIRccA8YEIySxBCoxSMRAAiUCCca5kAIkAimRlAKE4IIzjhBeGEtKqd4oGy3O9SmD"
    b"qBdVOFKXog6xuMQFvtRXOecYEAHEJSBCOOeYYs45wlhKqcyJASGQUkoCICQABka5wBJ0gSUQ"
    b"hCUiTCKJkESIAiIgAAksJRdAEQFE0NNLRE9fGGN19eq9ulpCiBAChBSyIFgDhDgTBQgBwFhh"
    b"OFbOc4Y4IEASUYFBIikJCAAQ6l6Uu6iDK5wqUywsqK5BfU29SLlcVmhfOKAy3OIbyoKLqxec"
    b"gwSCMcJP8akWREokASOEF79FCBEMkmEMCEAiKTESAiSigLGUgIQkgiMpJQaJEEiEAEuQi5Vb"
    b"vACAUso5V+u/WEuMMQhJCQFAAEhKAISoqSOKcpaBFAQwRkC4RBJxRCRIjFFRFFJKTdMAIE1T"
    b"hJDneerDTxnrU+CiylKfMoqy9xOoP+UyjDFCSDCOMZZcYIIFFwRjkIAAhFT+hzkCqT5CCIOk"
    b"HLDkktAcSQZSYkSEpIhIJEEKgQCBxBIAhJRUgAT0M7/7FN6FEIt1XiwnIiARCC4wxgUvEMGG"
    b"pcdZCgXHAAi4BMwkSAAOmAGCgum6LqVcmAkAoih61jEXFvi5EyFEnyXRBXwU2pV11CEW31Fw"
    b"ZYwRhEBISgnnXN2hotKn7KbWRS0RRghhCUhyJCkSEhDGSCBEOGYIEAAgQBxAIkBP6ekJNAlZ"
    b"ELCClbqHJysnBEKY8wKAAmApJcFYSpllmQYYScCApJSFlBIjKSVIpOl6UWRCCMMwCCGc86Io"
    b"1M0+60AL3198KKUkpVJp4YOfWrT/308QJU+4XNkAQGIiAQmMACOk/GHBlIAKQrmKEFxgACKR"
    b"5AgRxIUQIJHkkiCBEJcIECCElZ0XR1BXyRhbfLKIVuq/EEGMM10zMCCCkWEYrMg5YxJrIDER"
    b"ABIYlpIQggmA5KzQKDEMAyGUZVmWZcolnyWfxZsFup+44bNm+tQ3FObV2iobC5BCIJ1SQ9dY"
    b"ngshcsawpguCpFo4CRgQlgAAAiGBAAGRIIVkUgIBwCBBChWZEQJBkAAAEBIBAVC4WLieECLP"
    b"c855nueGYShCME2TMRbHMaUUY2w5dpExkwrJJKaYYhIEGSEESSKlQBwJxAUCjCSAQIJblqFk"
    b"gdIKykwLbaQs8KxieHbZniipxXIplC0ihfrep8JlkmWC8HK5PJ+HAiAVhUZ1xrlBKJYSOHds"
    b"K4oiamiIGEUOCOM0LWzLgDStlEtJmnvlGjWteqt5795dJtl5/8w0TRPrmkWLgjHGiqIwDGN5"
    b"eRkhdOXKlRdffJExtrW11Ww2syxbW1t78803Hz16ZBjGn//5n8uCT4cjy7I8s8SLQiMUOBCE"
    b"kCQcOAKiYcw4I0i4JTdJc7UAC7aBpzHxUyypgLLgdABAKysrCy36rGhYWGrxSwAAjKSUlNIi"
    b"yzVNo5oBGgmTGGGsUSqTnHJpG3qR5abnzKJQN5w0yDXD2rm6Vam6lzbXl5vtPM/DKLFLFUGQ"
    b"4diO587n08P9gwd373W7XcuxNU2rVqvf+MY3Op1Oq9UKw7Ber0dRZFnW7u7uxsbG/fv3x+Nx"
    b"rVaTUh4cHL3+2me+8+2/GIyGf//WzSRJHMvNotjAFGMc5SlQwhG3DN3AKEmSjAv5hD+eCIhF"
    b"+HrW6Z6lqp8Za3l5eeGJi7jzrHUXOISnYrVQq4cRY8K0LKJrcRxTQJhLkxJCSFrkYR479crW"
    b"9sVf/+VvCc5Hs3E4n1y5dIGlyf7uY79UGQ6HS5ubkyTe3nmuYrnT0RADHB0dbF3YYYJfvHix"
    b"3+8XReG6ruu60+mUUvqjH/1I07T19fXbt29fvXp1fX19Pp9rujkcDos8bnXaN299+O/+4tvZ"
    b"NCCcszzVTD3IUoRxqVTO4gQXeRRFuu0yQM/qA3iqcp+1y7OAWngoKZVKC1g9+0b+vDj82e+E"
    b"pIQQQgTnBBNWFFiCTXWDUFnkjLGc56P5ZGVz/Ytv/NKXv/zF6XRUb1bvfXxvZWn59u27hmkl"
    b"afJ4f7fRbHV73Wsv3tg/PEBcTsYjKUS57DMutra3dnd3m80mxng6nU6n06Ojo+FwKKW8f//+"
    b"1taWpmm+7xdFkSTZxUtX0jRptOqVemU8m3/tq181Nf3ezbdWudw0TFenjm0OZnPGhRBcNwyB"
    b"McDPMKEY+T/mdfj5/OGJHZaXlwkh6sfqDef8P/794k+CsHJ4KaWmGTwvdEwIwppGqK4NZ5NG"
    b"p/mf//G/sCzD87w0i6I8jKKo4Xf2dg8P9o6TNF3bXn304P6039+8sO1W6n6lWi1XKEiKiWub"
    b"luMxwTVNs2371q1b0+m0Wq2qdAQAXnrppQcPHmiaZpqm4zgPH+4udVYQls1WOY5j2yrZrvPw"
    b"4ScrQdL9n/63Vcv+SM7/rzvvDRuNKSUYYykEy5hGqGKrZ9X5p8z0rIhf/C/xff9TCFr44Kcx"
    b"9TQBzPOcGBoimHNBELY0I01TwJBK/vqXP3/l2tVrly/NBsPzT3bXbdcaDcb7h5mQh+f905N+"
    b"tVp3S6VWu/X5L3wWpBRc1KrVw6NjXaeC8ZW1FUyopmmz2YwxVi6XK5XKeDwmhBiGMR6PhRBh"
    b"GNZqtdlsVq1Wi4K1Wm3fL2kaTtOkUa4fPHpccexNJvl3vr+ZMdvSj8eDY8nmOiVUL1KuaxQj"
    b"/Kw54OeV+qfM9GljPctw8DQ0fEp0LCzIBdctkyMoOKeaDgCcMaJrYNKrL7344msvv/baa3sf"
    b"ffzKxsUvbl+bvPlu7//4t5vEYJ2mqFV9u7a6vP797/3NpUs7w2l/bX0lmYdxELZXlh/v7Ukh"
    b"HNtqtztBEIzH40qlIqUslUpCiHa77bouQmh7e/vhw4eMsRs3bpydndVqdQy43qgVkHc67f5J"
    b"b7XapPNo+NZb1aNDn6WYiPM87dVKY4RsaeoSU0qF5IyxRUCEZ9TSs5b6j/UmUVezkAgL6z4b"
    b"FDDGSqhIAE2naZEJCZRSzgQGIBhyzr71W7/5m//J7wwns7Nu98bly/FR91q986P/4V+/hmj/"
    b"8OD1P/z9292ua5QIpl/8wufffvcmYHnvo7ufe/X18+75jZdeoZRolCAsR8OJRHD9+efH43GR"
    b"5aZhcCFs2xYgJ9PJxYuXz7pnb7zxS75XajbrIGSj0bBse2WlAxKSJDt7uPtyo3n0ve9Xe+du"
    b"nmgI7OXOXSFDy4GCZ0nMBONCPF179FSiP+txQoW6Z3J59BRZlRLBSEoghHABCBMhJMFEiUKE"
    b"gXOGKeYgEEYCBKFY1zVWFBrGlm6wPA+i+R//yz9eWl1+tPt4qb36pS98Waf0pfVV/N67wTtv"
    b"11maAHNvvPDKG2+89MINx7ZXVtcKXrzw/DXHsdvNzqWLV0XBKMa1ur9/sK9Z5qVLVziTQsg8"
    b"ibM05YJZtpMJrhnW5SvXoiDyXU8jMOydEQLNzpKUosjyOIp119lptWrD8Z3/8/9eFtjlQmPF"
    b"MGdf+S/+yx/evUc0cH27YFkSx6ZpcS4p1gQXmGqMc0KxFBwjIBiElIAlRkgIrkymPI+U/ZKU"
    b"EkCldQghBFICCKnUGkGEEELJk0KVBMaFrhtIIBAAjF+5fPlf/vG/WF7prKwsv/LSLxCpGZph"
    b"2+YSQt1/+2384JMygYygAaGXv/Tl3ngcA+KSb13YPjs/QRhZlvfchR3OmOs5Kxury6vLB4dH"
    b"UoDve+PRpCjyleVlTTdKvjcPQr9cmk4mRZYVec6KIpgF+weHzaXOZDLTAbfbnVSwDsWj7343"
    b"vfWBR/JOp57OZplp3+wNv/67v7t1aft8PJiPp0TTDMMUEhREWFHohg4g5RPHQgghhDWQSJVU"
    b"Fh5G/JInhOAIcSEoQlIKJKUUkhACWCo640wCl6gQRGJCDYRpyfYd2y3ZpRdeeGHQ79Vq1Uql"
    b"IgsZjkPHMGv1isfzv/2T//qaYcqiYFR7dHq2cmGnK8T+dFKI4qR70D3rttudOI1n8znWtOFk"
    b"GqT5rTt3r1x47uz0tOSVoigsuBAgEIAoimg2ESznLIvC8LR7pulOEIiNjYs3336rXq83a/Uo"
    b"jgTBDSlGf/Zn+tnjGPrtr7x2/tGuMEpzhJ16fenyxa1r1yp+9bx7XggI4sg0jSQLkeAIAWec"
    b"EKpjigQRknAGSFBdsyQSUoqnxvJLQghJiJCCIgziichCBBTKCCFCAiWEYqzrpl+tzCbTql/b"
    b"WNnY2NwqV8qf+8LnZrPJ+trqdDwydCucTgyeJe+9h376Tj3P3KYX8oxIkgAe1+t7cVCrlQtW"
    b"TGbTw8OTyXjywvXrURTuXLy0t7+/tbnx+NGjWrV63uvnrNjZuZjlBSU0TZI0TmrVChN8NJ4M"
    b"J7PJZNpsdPqD/t987/tUI2XPK3m2LIpKGL/z3/3rNk60Fq9cWkHjOIxFwuTqxYsf9Lr17e16"
    b"vTmeTGfhdB7Mmcw1QnSNSsERpRKgyAspJNV1QnTOQYDACCH0RIESv1yRKihIoBgAJCYYYRBC"
    b"YIQoopTqEhFJiACQGP3CKy+ur608f+X5X/u1X3dLVSah3q6H8dwmmu+7VsWxKFyteJ98+9+5"
    b"e0daPq987eWTh3cb0n10cvYusN08vrix8c7Nt8u1xnAw3FrflJzv7+3pGt59+IlGSLfb9cqV"
    b"w5OTLM9ty07i2DXtQX84nMxXNzYf7O7vHh19cOv9IJyF4ShJw/FsrlFiWebbP/67O3//95Ob"
    b"79Z2T1wZV58vG1VNi0XvbKhrTiDRrFXtCb66upYV+d/+6AccCss2MEFJGDqOm+QFooRijDBC"
    b"QjLOBBJUIwAcIXjCWaVSCRBSFc4npI8RICSFxAhhwIAQA5AIABEE8uR4/1/9q//mF155RQCK"
    b"stS0zFk0vXrl4g9/8IPW0tI8T808XbWdv/tv//tlxqoVzXx5JTo9cOeEU+cHk/O84nUPDpFE"
    b"pyfHWZq06i3bdqbjked6nBVCSp0amJJ5EDElRCUYVNM0bWll6fH+/sHx0Y/e/DsheDCfLq90"
    b"Dg8e3/vo3mAwvHX7/cHB4fjOx87J+SWJZNpf+sIGaAkut84+euSCLUx7z6A9ySqVmq7rN9/+"
    b"aaVaDsPAtmwNEwC15yIl4xghTSOYoAKxQuQYAQKkMmXilcoYsBQCSyRBYgJSCgCJJCCEKKYc"
    b"EKYapZqlG5TgS5cufv1Xv/7RJ/dSXmBK7tz+sFaxe4Oe1PSVzQt2qdIGknznr4u7t8s4X36u"
    b"DlXu6iTZmzHNuxWP9ieD8TzIeD4fDSb9Xnu58+prr08mgeOWwiTZ292PJ/PXXnn1//3bH25s"
    b"P5dkuWFow+EZRlw3affs+M7tWwd7+zwvLMt8/Hj39q0P8yxxXXPQO+/e+4QeHX11daOeh2Vf"
    b"uld9SKZADd6fknEyS4twa91c37h//97Ozk610njwYNcy3DzJ/FLJMPQ0zQCQoRka1aTghcwK"
    b"PReaoEAJerJ3Q8p+GSEEQmACEoBQLAEQAEaYYI3oBhcCUwpcABdFkv5Xf/InJ92upmvd89Nq"
    b"pXqw/7jZrJ2enEqgo9n84YMHm0QLv/s9f3DOxKT5+kVwYmJqwzsnulvtY/4f7j4YRQkn+nQ0"
    b"Ou+dJ1mRZGkcpcPR6OrVa0mS3rj2/AcffHDtxRdnsxkI0W63bFM3Te2TB58cHhzevfPR8eFx"
    b"xff75/1HD+6HQTAezYe900lv6GfZr5Tbr5ZLNBmtXyijFgKNg8RGgYrzNANrUq0Ulsm4sFzv"
    b"0pUrr7z8C7pGXccenp9zxoVEIAAjSjABISUWEgsQ0iAmhifJH6lVahghEJxLjhDCBCEhDaIh"
    b"TCQgjpBpWyXbRnmhMXl5+8Jrr36m014aD3vT2SRLYtdzBIfJeJoF0d7DR8FsGH18v3nn4RJL"
    b"9KbwrzaFHCLXjQ+HScbcav39k7NhVOwP5+eDcSFks9W88vyVF156XgjePz3znZKUwnTM4bDv"
    b"ulbJcygBznkUp17J/+jOxycHp7PxPE/S6WhEERYFIwQIB0NAG+Afmv5lCknaa33uEpAp4Bw0"
    b"Qr3O4Z0BojVwTd209ruDytLKJJiWq/4Lz1/97X/0W0SSx7v7wJBumIZlFoxRRCiihGGbOhiw"
    b"quRgjInruAghTdcQBsAyyzJbN6REBROIEialX/LLbilLIkLkf/bP//na2vp0Pvvg7m0hRffs"
    b"lGV5MBilvZEdJUdvv50fHqwH8Y0MzHzmXbKNNuY4x1nuYm/YnxvYHZ/3QhCEgUU0wYokiRzX"
    b"Wl5fnc7nL11/YTaeSIIn8+k8mF65cnE6GZ2dn21ubecFm8/Tj+8/GI0nWRzprKhpOoqCioS6"
    b"gE0JVzT7myubX213cNAzG7h0sQ44BFxIAIRsPuTxPOdpLMPYN2yYzzumUSLQsKxkHrz62mfa"
    b"yyuzeSgxns1nUvI8SUBKHRlCCAlIwpMtCFKt1BzHSbJE7Z6US36aF1TXDdtiAkq2wws2HY9e"
    b"evWlf/jbv75z/fJHd++MZqMHp8flVh1TEvSH5iyOPn5AHz541TQ/i61LEWswmeFZ64tLwgyQ"
    b"TpHQkVU/uvXYFd6l5taSptdkYeQxKXIOvEBo48qVSThvVqqEoqRgTIjnnts+PjlcXl7WdT3L"
    b"JNHNB7t79x5+0hucFvFsydK08XgN4CvY/KONjT987vIbldYOoXg2CcV06aWO1sBAMzAIAgGF"
    b"oFEaDsZWgmqxqPb75uN98+zUGk0263VT09/96GNarRDHfv/ubQ2BZRBdQ4TIKAmFEIBhkWRT"
    b"XdeTLDYsk1KchEGapkAw0vSciUqlIvJiudP+w3/2T2vtmkBcR7IM+MO33t3yrXJvmPb6mwKC"
    b"h0fXNKtWq/h54sShAyJmKa4DOCCpLNLMBB20wu/YydnAMcVnGs7VpfKE6OeA3+92Ucr4W++9"
    b"cOVKIwgnYaJR3XLc27duCeB+uWLqRqdU6x0cf23n4vDv3wxOumu+e7lc3llZv6DZjSytZDN9"
    b"uBfEEejYbPidrQ3juQrIIZMcFYxIAXphXW9eMLTRfjw+2q3oZt2wZr1gPDj5uw/fE0vLsL65"
    b"H0V73ZNv7ly4d+/+JEmmQs7z1HBtVggmuEoPOedoe/s5x7MHo5FOsUGJlJJTygH5dsm3SyXb"
    b"+vwXPvsPfuub773/9vWdC+Fet7h/Jk/OR4/umMGkKbg2T6p6mScJpmkuxrkWI4OtrK1Ury6B"
    b"PU5FZFIXMglAICOzR7PjR/08k5TbpixRahcaTSmJJNB2Z/P11xtvfAlMfaTh79/+cOXSDhNQ"
    b"081sb3+Fw0ff/e7ko3ulvGgZOkojW8N5FAOOmBg5FbS2s6RvdoAwQAVABhpiIKTkGnCZc0RM"
    b"EBogC5gePjwORln3cEKl7WjlrACgeka1IRFzzeLl+g8P9z8Q6USnUZRgjDGgRS8IWl/fJBo2"
    b"bZsXWTge11vteZaZjqtx3KrUXnzh+RduXMceXW/U63G+9703szt7tNttyrSUhk0E+WyONZqI"
    b"qL7V0Fs63a5BiUCeACRgFIAlSzjVDRA55AKQB7QMCS52e7yfn++embqdZ8I0y3OinQE+B6hf"
    b"u2i/eG3lV79+dzySmtECNPj+D+c//Wml19skxCsKnGcIi1E4qq03aleWYdMFPAcxB40VLKGU"
    b"Ss5BIqbpvGAWxSBFDhIRTAEhSQC5kGCgLdjth7v96eHQKrBuOnNKI9MZYuvEL/37ZPxhPEs5"
    b"IlTP0nhRkkFrK+tUJxln5ZJbc0qTyQQ5NkJkudxcbnfcshtl8atf+IXnyzXr7Qe7f/btZRnX"
    b"QehFriGpG7iyUYe6gK0KFGPwNJmnUhYYBCQBuI7kDBEKRQEYA0GAAPICkAXUhVwDrQJ7YxgV"
    b"4/1xEjCGdKQZWVY8NLD3T/8x3HghYNLsD8Nv/5X/8OG2KOw0JoSEedDeXKZffRVkH9gQcAyU"
    b"ySIHzBElAAKQAEAcU8aEzgFhIoFJyTGinDFMCZIaZBpACUgFaB1+8O7wYIBNl4OWMTJo1L7r"
    b"sL/YezgTmjQsLtmiUkia1YaUglCSZaksWKVSo4ZuaAYwUWT53uF+xvLllfbF1kqn0B/evFky"
    b"pCxiHVOQkPIijCdMBroIcbsOWYI0EzEBLAOdqu4H4BwoBZDAJRQMqAmCAtLB8JKHB5OTwfhs"
    b"Mo8TTnSwrCAtcgnnUq7/yldTz6202h7VnCCcnJ7wLBUaiQhI05gk0/13f4rCgU0AV1oAGkIE"
    b"CQKIABcghQTJOdI1AwQgDAgw4gSoi7mGwADiAC3BUf/83v6DH97MMpRTOzasKdGgVDqj8v35"
    b"cIwQo0bKOKE/6yZCWxubVNcYY6qXiDHm+SXf9yt+lXMexyFg9K1vfdNCaLvUSI+O5g/vuKMp"
    b"OerVcuaLXM9jInJARZAHpWZpeasNDRuaFqAAaAqSgYQnzTWcgKhAgOTxqHswnJxFruZaGKcA"
    b"c4OMid7l9MJnP9+4ek1bX3u7f5aWXLtaF2nKzs+dMIx2H0X7e36SNHjhhoHPUr2IRBoxIFbN"
    b"ru1U9K0GGBggApJIYAhrknOOGQIgoIOwQPoQAds7TwbBYK9nEpsQJyd25pbHun5E4P3zk1tH"
    b"h1NTsy5s5oYlMI2SbBbMf1YuvnDhAmNM07SiKAghtm1rmlYul13XPTg4yPNc07TXX3/96tWr"
    b"jUZj1jubHezVMrYljEc/+tFGpWQkicvBkgCS6TKDZJrxOfbh4mtbpI0lzSQXmBrAaXoaHr59"
    b"DJGOtFIBjqaVC4k54SFlSdkuX7n88rd+FzrLc5C3jx5LakzSpFSrPz7Yv3vrdtP3YD7f9ku7"
    b"b/74zve/9+X17XXbqiNcxhTSAkMRij6DoN1wa8uudbUJOAPGQSMMZzIHjTaCj3u9x8N4xDXk"
    b"YmRhpEcFLwwzNOyf7O99Ek0fABsD4Go5odir1k3bIQhPp1PTNLMsy/NcCEHUVqVpmpqmua5b"
    b"LpfVjnSv1xsOh2oz6uDg4OzsrNPpHJ10Hx6fbL14Y67RUcn+zsHjm3HwTjTbJaKngd3soESr"
    b"GzU9Fr3Tk/qNbYQSZCAACqL08Id37dQBXB2YpXG1eRfkD2aDv44Gh8v1pW98XT536bAQqWnd"
    b"O3qMdOqUnN6gV69Wfc+plksHBwd7B0fDKG5fvPThSXdPwj0hPqL0bp6zqi9tx9J9l1l0nM3O"
    b"+46NacUCTDgwIFwTRnEvObh54uY+luWBcM6t0kPHWPmdX7+/XP0fb//0A5TvUplaNvHL8zRH"
    b"1BAAhOiGYVq2kyTxz/bNqtWqpmmqP6IoCsaYaZqc836/H4bhaDRSOxqGYezt7Tmu+8prn3Vr"
    b"9ZVLzx2FQez5XcH6kp9k0cOz0/3+kCEbC9xEBk7D8oYHWpaxlAoNztBwdyZRdWL6b4fxj0fj"
    b"PUqGNf+0ZLY+8xlvY4vUW8LyRnHcn4zOhwPLcRqNxmg0jKOoyPNyuTKeTVc2NkZJWtvaetAf"
    b"ZH41rdSO4uAsnI/S9HQUmnqpabkyTVMRl9ZXAXLVl4VxtfvmMU7LM80bl+rX/9Fvb/yDb1z9"
    b"zW9NllpvTfpBrfJwMpkDFpqZMSiXq6ZpYUxynumWgSlmjKkWIQAgjUYDAPI8d123VCppmoYx"
    b"Ho1GSZLkeU4pnc/nRVHYtj0ej3cuPPeNr3x1Nh6vry+7rldvLBFs7h3sVZuNUTiv7Vw4MpBW"
    b"Ka1loiSSWA6dCy1KAbiTPkiGA5j59ffy9C0pxu1ml2Wd5y+vXr529fpLnukNeyPOeZzGQPV6"
    b"s3N21g+jmGg0jkJN09IkJhidnB63Wq3Nza3NrQvzIHy0+/iLX/3KBw/vh7b9kIvDYFahxDf1"
    b"cDZvX9gCGiGcITBQ5sw+HOZG48FyZ/Of/ZPJxc1Jpz7VdbPR8MqN/+V//l9Lpn/98vPzSbC+"
    b"tjrsDxBCUjIJwnRMQJAlWZ5laZoyxki5XEYI6bqOMVbIYoxhjLMswxgrFiuVSnmet9vtLE2/"
    b"+IVf9H1PgqSGYdpep70UxoHtWmAY/SwtXdh+7cZL8MljX+YBn9a2l4GnQMuHf7uHtdaeY/40"
    b"nHf9kr667DXqO1evXXz+xc7SSjKLmo3GSfc4L3LbcYfD4eHB/tHR4dl5dzIeI4QGg9777793"
    b"enpCKOksL13YviCkHI6GJ2dnIcunUswojdO0VBQb1borkAcp6WhABCL+6G43Py4GYOFfeWO0"
    b"vXGKud5qSE2PM/bOzXe//Iu/1Oks/eW//w5nLMtSSggrMgm8EHmpWpZS8IKpxliMMWk0Gmq/"
    b"VwihaZpySc65pmlCCMdxbNtO09S27SiK3vjKG612u9ps2iWXmobtOH6lRAkreaWdS1edUvnF"
    b"ay9fX93Co+Fs2IU86bRbYBEYZ/NbY+K230HFe3Hw/Be/7FSqrUr9heevbz93kTGm69p0Oj7v"
    b"nyZR+PGdO+fdk/PuaZYkvfMuINTtdo9PTgnFtmMDkpZtv/LKS4atDUc9xzVNy9p7fNCs13XG"
    b"o97o+a0L+mSmy8S5Uoc8BVYe3TomsXGOjJXf/e0TnVx4bns+mZiE6ongM3UAACAASURBVFRb"
    b"31h/9Hj33/zZv8EUu54DSEwmY0SBaJqma6VKmVIKXBq6YVmWbdtPdqQRQpRS13U1TQvDcD6f"
    b"c85brZZlWfP5/MaNG5Zl7ezsjEaji5cu1hr1QkohIYkjnYiy62JCbM/vtFeno2lw3qtiPD/r"
    b"eoWoCElXmpN7+2RsTWjpr+bDZGM5wrjZbOlEf/mlV9I8FYIHwXw6GX388b1gPndMXfBC14ht"
    b"WZZtTydzLmSW5VLINM+/9ItfqtaqGCHLNpuNuqZRIUQSx/v7e2XXmc7nLdfbQaQYndQu1YAQ"
    b"mOmnt04FdqyLV40vfc65cKF3fOzquqkbmOKyX7l05VKeZ8fHRwAySZJavW47rm7qpml5Ja/I"
    b"eR7nWZYlSZIkCanX6xhjSqmu65qmcc4ppXmel8vl2WzmOA4hJEmSV1999Rvf+Mbv/d7vAWAk"
    b"iUTY0nSRxHkSaxSDxK5XSeOs0WwZQtYM6/z+w04BcjItPX/t5OYdkXvTcuN/P3xELj33wssv"
    b"UU2/dPGSaZhEoxTDw0/u3frwA5CIIGLahpDCsm0B4Nje8vKqaThFzoN5bFue53qmaTuWHYZh"
    b"uVQ2DN2yzCCYBrMpR5LWaslg8EXPL+czzeW01oZjNjpLR4J6L72Ybm08HvaXq7UiTommhXEk"
    b"EZrP5+fdXpFkLCsQwkEYMS7iOM3S3NEdWUjBuZBSgYnU63XVzLboDVFtlgghTdMIIbquU0rf"
    b"e++9Vqu1trZWq9WlBMu0JBcsT8p+yXU9ADSfB5VaxXHc8XBYFBmN4kpvaEeJR0jvbEL9pb/v"
    b"9Xd939za8sulC9ubJc/XdT2Lw363W+TpbD7vdFYkoCxLbcdeWlop+RUJOI6zTx48wBiblkUp"
    b"DYJwdXUlzZJ+v8cYG49HVNOuXr3y8e07WZ73o8hI0i9XK24eh3zmb1wM3j8OM+MQ0e2vf/3M"
    b"MVYuX6ZA8qLIBa/UGrppdM+6gonpfDYYjSeTaZJkSZwgQLpueJaTpUlWZFmeq+1+rFJqVZAv"
    b"igIAVOPdfD4fDAbT6fTw8HA4HH7zm9/87Gc/6ziO69q2ZyAETBQSkUkQ9MdjhsTa5lK5Yhcs"
    b"Bs8I6s68YkksHETHD8+wUTkhcMRz07bf+MwXlipVDbDkYu/RLioKi+IP336nXilvX7hwcHLa"
    b"7Y80zS35DcaRJDQuMmxocZFgg8RFZJXM0Ww8nU9qjfp4OllaWz8bj2fz6PrFq1XbK7ueWfZO"
    b"eDHR9WE/Ba0xOhzlHNs7O42XX75w5bqmm9zUccm1fD9J8+k8bLQ6DMO1l168+Pzlcq0czKe6"
    b"RgydOrapO4Zm6/zppiHGmNTr9QVnqR5eAIjjmBBiWZbjOJ7nra2tua7red7q6moQhQAQRRHG"
    b"2PNKlGqO45mmLiUvlUogZLVWn/HEzlPjk4fVgnMGoWYc2NrfHO197Q/+iV2rIMw1SqbTWckt"
    b"9c5OBeOWaz/c3bt17+OHj3alhCIrPvjgg5s3b773zttHx0dxOOsP+oah3/3otgRx4bntLM9z"
    b"VkiA8WS21FkJJvPVerPVbHzxK1+90GktgyhGI09q1X5YBHyENf9rX2Pb24MsC1nBJDdsazSa"
    b"zII5pbTbPQGM/+r/+c5Z9/T2rQ8dy6IYFXkmQRJKclYQ/KSszBgjvu+rXVXTNJVWQAjN53OE"
    b"UKlUStPUNM0XX3yx2+3W6/Xl5eVGvQ5AOEjb8YjALBcYE8aY49hxGBVBdt7tSYocxsrjIO33"
    b"LayFGrrva5/9oz/wN9cH0QwIcjzXc73JdOr5/sHJySSIjk7PPrp7P0+zfu9s99HD/b1HRZbq"
    b"Ou6fd+PZNArn4Ww6HU8Nqi0tLY1GU9fxdMOkWPMMz6YGwmJrZ9v2SpuNxhsv3bj9H95sCYsP"
    b"Io2QEyKXfue3dwm4tZpt24TiKAjyLHVsy7Gtkuf86Z/+6Ucf3cmSuFmvIyTjNNZNfX19DYHE"
    b"CBUFWzQik3q9TilV6SGl1DRN3/c1TTMMQzUFn5+f//jHP97Z2fmDP/iDVquFMS3yPMtilhdI"
    b"Ytu2mRCaRhkrXNczsSEQEEvb7nQuN5c++PFbDkLngj3/R/9p63OfyYCeDYau75uWNeoPszRP"
    b"s0Ji7HjenTt3DM0YjfpBEAjBNEIRllmcrK2snpx0CQLG5fbWVpqmrVZHCFHyvCxjrXrj44/u"
    b"hUFgOGZ7dRljUnbcoN8fPz5szLjL8RyJdLW99fv/mC91wiicTCd5lrKC1ao1goll6pZp/uLn"
    b"Pz+fTAkmnPP+YCCEMEyTFUW5XC7yPE2zRd8pdV1X13X0dEaHcx7HcZZlURSFYZjn+cbGxu//"
    b"/u/HcXx2dmYYhqlbjOWTYU8y7ji+Wyr3p2MhhEXIgDEEmsTCccxZEATNVrdSteZRbGqXP/eV"
    b"t2bjPJV1vxGmLIwmRZQEs7njlbrdbrPVqpRdkDzPK4Peua6bUZ50Oi0w4PC0SwxjHmc05zsX"
    b"Lx8fHo2HI9u2j/cPpZQyy278wvN3792PJWJIH45PvEZj5fLl6vPX04MfCoyGlK5+5vWzyehh"
    b"7yQYT8vlcqVSI4Scnp5mSVpyXdu2b9+9++jB7s233zIs07As3TYAaeVKYz4Oi6LwvVKcJqrB"
    b"mahuZc55EARxHOd5rpxRSlmr1UqlUlEUN2/e9H1/e3t7eXk5DKLxeJRG4crKSpqmx93TNM8q"
    b"lTJFVKc60WmYRnEaGZrOJa53lhjA0quvPkAotZ2D/f0giFrtJcZ4kWWWacZJsr+/f3p2Yhp6"
    b"tVq+fv36/t7hdDbzfd80LcaFphuAsK4bW1vbCOHReNJstAAkL4ovf+lLEoAQbDmOZtmaYXiW"
    b"aVp6iuSF9vKjv/5b07QfUbTxja/1LIOZemepwzkDjCjRhBCu49RrtTiOf/zmm7bjNFsdKYFx"
    b"keeFY9uu6yZhAiCDKMjyDAAopcSyrCRJlLyyLKtSqViWpcxnGEa/3zdNc3l5uV6vX7t2bXV1"
    b"1S+XHNcVUmZ5YVluuVLWNA2k1DSKCQYMpmGYpompbpcrncsXL37jlxuv3pC1MifIMM00T7ng"
    b"o+FwdWVpOpuenp4MBn3TMNvtzrvvvbe5tX3x0qVavVav1waDvq5RKcX29tbW1mYQzI+PjzBG"
    b"tXotimPP8wrGoihqVBonRycbm+umTpuNSl7ksUhcaozvHR9P4/zS5s6v/so5iFEUTCYThCnF"
    b"WhzHYRhatiWlNEyz3emc9c6Pj48eP96dTif1WtXUdQApAbhkiOBFdyBpt9uqhrVool8MTU2n"
    b"00ajUa1Wf/mXf/nXfu3XNjY2pJRZlgFApVKlmq7pehiGWZphhOM4xoQoSBY5G0+mw9lslCbD"
    b"PH086BPT4JzrhqHpmm1b1Ur5/Pw8y7LV1VVK6enpqaZpP/nJT09OTh8/fjwej8/Pz9UEhK7r"
    b"8/l8PB5zzofD4erqaqfT8X0/y7Nev6dRjRfywnM7aZGF0azsl+IsSXjGM7axtFna3nReufrB"
    b"4HTKC4mg4lcFF3GcEEIcx9E0rVavlXx//+BgNBqpWQQEKAyCer3u+/48mBWMPdsuSlZWVlRo"
    b"zPM8iiLOuZLys9lM1/VKpaLr+ttvv/3jH//4+vXrtm0r751Op8PhsNfrEUJc11XATJJE1X10"
    b"XXccx3XdoijiOAaALMsYY2EYAoDjOKPR6PDwEADeeeedIAg8z1NYPjg4IITMZjM1fCSlDIJA"
    b"6eTJZNJqta5cuXL//v0wDMMw3NjYyPKcUD3Js73Tw6TI4zi2bHM8GMdZNtNk1+BRxZSuIwDC"
    b"IA5noed4ruthQlRxhTGWpmmj0fje97734Ycffvzxx7PZzHVdy7LSNFWIYYz9XE8pxjjPc8aY"
    b"ZVkKXKZpUkrTNA3D8Pj4uFarfe5zn7Msa2trSwgRx/F4PC6VSrVaDWOsxmgAIE3ToiiCIFDo"
    b"U3rN87w0TdUNh2H4+PFjjHGapg8fPtzf3280Gufn5wcHB1LKpaUlKWWv11MiRhVCSqWSwtfa"
    b"2lqz2ZxMJs1mU9d1VXQzDKOz1CGE2o6taTQOw0/u3w9ngW5ZmUmFZ4VFESWJbTr1agOkZELM"
    b"ZjMJUrW/Z1mmadrdu3fTNJ1MJgihWq3m+76u62q0SjH4YtiEVKvVPM9VWiOfJkGq3jAajdSY"
    b"tBDi7t27v/Ebv6Fa0sMwrFarUso4joMgUJSXpqmaPAIA13WllPP5XEo5HA51Xe/3+/fu3ZvP"
    b"58p80+lUdf33+33DMNbX1x89eqQMoUq1jUZDpaXNZlOhO89zz/MYY5PJRPnBfD6v1+v1RvO9"
    b"d98ZnffTILZN0zQMyeVsNk/i9HD3gEpcccrn/X6cZtMokhgLzpTCFEKowsHt27fff//9oigm"
    b"k4myjm3bi0kV1ZSsckGq1k0BUplJeVaWZSqFbrVa1Wr19ddf933fsiwhRLVaDcNQCKEQVK/X"
    b"z87OGGNZlqmkUvmRmiEpiuL+/ftCiE6nk2XZeDx+//33v/nNb969e1fB1rbt2Wym6rHD4VBl"
    b"pmpaUhXX4jhWTi2edhnrug4AYRj2+30BstvtxtO567q9s/rSygo1ddd1TWpe2Nie9Id3T+9Y"
    b"Xqk/GDWXO6PJuOaX5vM5IcT3fc55kiS6rne7XXW/lUqFMTYej4uisCwLPZ2qf5I412o1xTiL"
    b"koNlWQBg27aatJVSXrp0aWlpaXt7O03TNE3H4/FkMpnP52maJklyenqqBoAwxp7nWZY1m82C"
    b"IJhOp2EYquXinN+8efP8/Pztt9/WNM2yrF6v1+/3Fagnk4kaAKzX6wgh27abzWZRFItJCiWg"
    b"B4NBGIaWZYVhOJvNGo3Gzs7OWfdsOh5vbWz4rut7pZW11VKtrulGOJ7lcUqp5pZKpmFU67Xu"
    b"8FyAoIAE54ZhnJ+fLwZ2Dw8PGWOq1V4lLZRSVVZQ/qgolVSrVcUviyZ4NY7HObcsq1QqGYYx"
    b"Go1ms5mmaZubm1LK2Ww2GAxGo1GapgDged7Z2Zm6k+l02uv1Tk5OkiQJwxAhpNbq7t27juMw"
    b"xjzPQwj1er2dnZ0oivb395MkKYqi1+sp3TsYDBhj/X5fYUpK2e12kySJoijLnkygmqa5urqq"
    b"qpIYQ7PZiKIQABm67pQ8apqnZ12CMOM8jKMsz9M0dUvO8upKrVKdTaaNel3BQoWmv/zLv5zN"
    b"ZnEcL/TAsx3KCkYqCySKpBe1B0KIqm0tAl8cx7qur66ufulLX1I7Y0EQqHinaVqaplmWKYKP"
    b"okjF4NlsRildXl42TVONaE+nU3g6xut5HsZYzVCoK1N7S1mWVatV1YKheKBarWZZFoah53nK"
    b"E1utlmEYQgjP8zRNsywjTqPRaNjptC3X8cuVZrvdH40azWZS5HGe5UXRPT8bjgaT8Xg0Gk7H"
    b"I0MzZrOZEKLRaBiGcXJysre3N51OF9M8alwTANQDJBaDJ4SQJ8ha2FLdmyIgFQXa7bYK7Zqm"
    b"qRnhfr8/GAyiKJrP55qmNRqNs7MzBb0gCKSUlNK1tTWlnhzHCYJge3tb+X+pVGq324r7VM6g"
    b"VphS6jiOikcA0G630zRVgQlj7Pt+tao2fePV1VUVyxBClmUapnH9xeu+77c7bb9cNi2bEu38"
    b"/DwMgrOzs0G/v7zUXl1ZNU0TI+nYDsbk/Pw8iqI0TZvN5vHx8U9+8hPHcVShZQEXdfzFuMCT"
    b"aFipVJ4dUlmMRT1pskFoPB4rvbO/v6/reqlUUnJRHfHRo0d3795V2dInn3xyfn5+cnKibnsR"
    b"UFRwYYwdHh7u7OxUq9UoigzDsG273W4rfacCU61WGw6H5XJZ7chVKhWM8dra2mAwaLfbnU7H"
    b"sqyiKJaXl1utlu/7g0HfcR3bsggis+lsZX19Np9RSj3bNhDaXl0rOU6eZUEYbj+3xRjTKN3d"
    b"fbyysqKWZ29v7/Dw0PO80WiktvsWpSv0zDz24kVqtdqz4ylPepifFk4VLIMgYIypyNhsNlUN"
    b"59GjR0dHR6VSqV6vq+1YSulwOGy3261WS5HiaDQCABVDms3m2tpaEATdblcRZ6lUiqJIsdjW"
    b"1pZyvaIoqtWqrusK0a1Wq9FoKHKsVCqNRkOxr+/7CKH19TVCyXgyqddqtUadFzwviul05rme"
    b"QahtmIBRtVbLWXb//v2XX355PB6vrKxOp9OTkxPLslZXV2/fvn12dqbcbfGQFPj5ocsFxIgK"
    b"QPDzY2QLga+uUkqZ5/nm5uZ8Pvd9X7Fvq9VyHOfZ2wiCYGlpyfd9Qsjx8bESrq1WixAyHA7z"
    b"PB8MBnmeD4dD9VsAmM1m7XZ7PB6vr6+bpmnbdqfTUS5frVbV4wmUWRUclGqp1+tHR0dra2tB"
    b"EJZ8H2OSpJlhWsE0rFZrgCBjBcJIUjyNAst1KKJLneUPP7hl2Y5lWdVqtV6v53muqGM6nSZJ"
    b"smDtReandrwUyp5gSHHqsy9lKcVziqFVCB8MBlevXg2CoFqtViqVXq+XZZkqEHqe98knn6g4"
    b"pUjH9/1araYEEcY4DMOVlZUoinRdPz4+NgwjDMNer1epVKbTqaJCZaM8z3Vdj+NYSRPHcZRX"
    b"Kk0zmUwwxlEUOY5zeHhommaSpo5jO47nOZ6lG4eHR2EcAUKU0uls5vn+Bx9+uNRqM8bqzcb+"
    b"4YFtWSqAFEWh7KV24590uhOiRIOy2sITn0DsueeeU5ZTllr0IinGKZVKi50Ly7IajcbLL79s"
    b"WdbZ2Vm9Xp/NZkmSdDqdjz76qFwur66ujsdjTdNGo5HKxpWORQgZhkEpnUwm5+fnhBClAzqd"
    b"zmLdVOeFWhtFiOqlpK8iFCWvDcOYz+e2bUspx+Nxq9P2PM+kZpHE8/k848wuuVlRGJqmU02d"
    b"KE8Lx3PjPPN9//GjB75XUrJjd3dX0bE6/oKIVKBT+aOiXfUJaTQaCoELTKn/wxgrfl3MHgZB"
    b"oGmaitkXLlxQK2Db9vHxseM4lmVFUTQejz3PU5SHMR4MBiqGqiMYhqFqjSpdN01TeZlpmkEQ"
    b"cM6jKJpOp0VRJEmiYm4YhowxFbIV7tQBsyxTjgyA8yyP5wFnnOqUCyERSCHSOInjmOUFJWQ0"
    b"mXilEiKYUurYFsH49PS0KIrZbKbAruS3EkAKXGrN1E6zcklCCGk0GiopWayw2q9XV7ao1SdJ"
    b"opg4TdPr16/neR6GYaVSUeO3lUrF9/3pdKqSYaUD0jR1XTfP8yzLer2egqGqPbiuqyJmEAR5"
    b"ni9g5ft+EASqJqNpmoqMS0tLKu9ROohSqpIhdT+z2dQ0DSF4kiWMc6prSZxQQvI8T9NUSBnF"
    b"kWkaR4cHnuemSSy5ME2zXq8fHx8XRaHKG8p1CCF5nluWpWxnWZbqZPiZ5125cmUxt28YRqPR"
    b"iOM4iiIVGtQlWpal63q1WnUcR22IBUFQqVT6/b66PWXiyWSiqgvqSR9qs1aRmm3b8/lcSXBF"
    b"nJZlqTRQ1S1M01Rqg1KqHg6iwqsSvVJKVVwLgmAhhbrdrlISUsp6va48oCgKx3Fms5nSAepP"
    b"FdMVgaqd43K5fHx8vLu7a5pmHMeGYSh+VHBRBS+EkCod/ywaNptNIUS5XK5Wq5TS0WikXENZ"
    b"SjmaZVlxHE+nU3WmZrNZrVaPj49VOqkKHUdHR57nTSaTNE3zPFdlFrUVUhTF/v5+EASmaary"
    b"ofLEJEkWD0ATQsznc1W9efz4saIqFXYnk4mq9qh0fTqdEkKerXwRQkajkRKAYRgqF1MBrlar"
    b"WZalkj5VLKjX651OZzAY7O/vA0Cv16vVaooKFBepjRvlUiqZWTyHijQajfX19aIoVJIMAMol"
    b"VVqknpg0nU4Nw1hdXVXj8OVyWS2Uunld14MgsG1boUOdWGVzioy73a6q5auWExXsFKyklGEY"
    b"KuJTGY9qN5xMJqrIo7IoFeMHg4G6QlURjKJInahWq5mmqaSTWl2lzlTT3nw+V+5v23a5XHYc"
    b"h1J6eHjY7/c557VabTweqxtRiZRyKVUsU6nozzTqzs7OeDwGAOU4KllTjwZwXTcMQ5V22Lat"
    b"bhVjvL6+7nme67pJkiwWwfd9RW2apqnTCyFUgqlkmqpzxXGsCoSqfq1yoF6vp+u6gqSqvVSr"
    b"1b29vVqt9ujRIwUZ5R0KeipmqZYxlWk6jqOYUSFauZ6iP8U+qo6odFySJOPxeFGzVA/yU6v4"
    b"rCJVt6acTFVKSKVSUX6nmGIREXRdV25i27YiQl3XDcNYWlq6cePGIteVUp6dnSlmUXZZ1DQU"
    b"JG3bZk8r2WEYLtghSRL1uC9lPuXyKpBPp1PFDOfn59VqNQgCdQPK5dXmJkJoMBj8f22dyXPi"
    b"VhfFNWAkhEBiFFMDjt0e4+rOwulKUtlkl002+Z9d2XWlk1TKTrttYzCTQExitMW3+LVe6NTn"
    b"RaqbuAFd3Xfuuefc92Tb9nq9dhyH1C6VStRKiunLywsYAhLl8/lCoeD7PjIGgLANDzpCXwQN"
    b"Sa7NZsMHiVNFFExDOTys5+XlhYPtkCwAYyxYwzCwNn777TdQ3DRNSZKSyWS5XOYjx+MxMhAf"
    b"kE6n+Vrr9Zq2ebFYoEzxVbrdLqIzfb/v+7e3t6QA92w4HFIouHIGXyEQ9AaVSoX+yTRNFgQS"
    b"ueM4ME8oTrFYRAqm9H8eqFXV5+dn3/e5E7sSja7rREZoVpvNRi0Wi0IMpOHgekA1FDgOMVsu"
    b"l77vdzqdX3/9FcKJ0kLuULlgkoiZ/AGyPhgMTNOEFrNIFUVB6vF9X9CCdrvtOA60i8k64kIz"
    b"CNzA1GCMtm0vl0vbtlkHnufBQtFagyBwHAeEJh8pLI+Pj09PT7CE9Xodj8dhDxRQcToW+chV"
    b"fNaXyuWyFA6GcIIRwLQNjxBkxXLHKD30iXCCdDpN7Scugr8xxsR7Qu2AGPQpDgzjxjCxEwTB"
    b"YrGgPvDpICbORSQSwSe3LKvb7RqGEY1Gs9ks6qBhGJ8+faLHIiiMJdCBcyPJrNFo1G63//rr"
    b"L/xQaguJAkIBVf9GR1VFECRJUl+9ehUEAfcKHoSEJFokZDAwy7IsbjUIiv4XiUTANWQvVEfe"
    b"Z7lcsloBEaIZi8V0XWe8iYVGaQMyCFYkEkFBlGUZvgJpCIKgVCp5nhePxz3PI8uE1UTd4BAb"
    b"cJYifnBwAAqbptlsNgEy0genTg619l31ih9A/DPP4gTcbXiwKdEhxcRQDasdjvfq1SucCNM0"
    b"U6mUJEnIhC8vL8PhEImVCUwwfrPZPD4+CiID2fN93/d9bCFqkOhgqdbYB3BdWZYZna5UKjga"
    b"3BXK4mw2A9RZudyJSCSSy+Wy2axhGLlcjroxmUwGgwEMi09nYlbEQg6PvxXKzOfD+4IAzV2t"
    b"VqtKeG6dAC+gB7oRjUaF+F0sFp+fn8vlsu/7pVKJegwisi/D87zZbBaJRMAp+kHwKBqN2rZN"
    b"qs9mM3gDtZk2O51ODwYD13WTyeRwOEQOoctFU/Y8jyuHWBcKhfF4TJ9I4kiSxNQnUqJlWZVK"
    b"JRaLDYdDyIeu6zc3N/P5HMkTzBFE4T+6HsFinbEe1VqtJlzo3dNOqYDkGvLIZrMZDodYOJeX"
    b"l5vNhiacJPI8r91uJ5NJ27Z7vV4QHlhL6GErcNFGowE802ACQJ7n4c7yhuIAZTwFnGHhfUJi"
    b"1ut1KpWiCMKt0um053mxWIyhDdyzyWQCL0ELQw5iIePgkonIWOJHeKC7iaZWq9V/eUT4Q+0U"
    b"fRw3Qdf1RCIxnU7j8fj79+/fvXvHOCA3J5lMplIpJit1Xedi4PHgApnseR60G46O8kPIQCtB"
    b"cBaLRb1eJ7N837csa7FY8MuJRILc/3zDVRVUHY1GjPXT4pim+fT01Ol0yBdFUVar1d3dHdY8"
    b"vFLXdapNJDwV+T/IJTJOlmW1VqsJRYKUY6WIcTcpPH0TiMXuPzg4aDabx8fHmM+KoqB4CIAD"
    b"FGhWBDOAxENfc7mcLMu8m9ipQDGh6u3t7fV6vUKhIMsy7k6xWJzP5/gd0Wg0FovBS6LRKFWF"
    b"1YfSLcvy3d2dZVnFYhHddTQa3d3dYe1UKhWKFV46mb4Nz74V6h7BEhqyymwMN4pluFsHISC8"
    b"TjQ5hliSpMvLSwwSuK8cjsPNZjNkqVgsRvu+XC4VRaFZm8/nUFO+32KxgMTJ4WABVRWnM5FI"
    b"tFotyBQqBZmu6zo3qd/v826yLNdqNQoLXudkMmE/xHw+Z9BD07TNZkNBazabT09PQO1256w1"
    b"UdOE0qDsnOOqIuO9hKeakhf8SzACcgCWQe6Xy2WlUsGAAPjpctBCWZWLxWK1WrmuGwQB5sJk"
    b"Mmm327hn4vdJNNQFposURaHNpNF5/fr19fV1KpVC7TFNk4/j4ESyidixpqrVqrhUSDJ8hfx1"
    b"Xff6+vrx8TEIgkwmw20AUgkKiw41RRRHkTfq/v6+FB4XLKJLFZPCA175MIiloiivX7++v78/"
    b"Pz8HU3nT6XTabDbBBdFkGIZBK4OJj+AZiURs2wbLOW4UwELwgk+Tv8/Pz/F4/OLiotfrGYZh"
    b"WRbyA5ioqqrjOOVyGfXx6OgIOxI2EI/HwSNEyslkcn9/32g0rq+v1+t1qVTi4xik4GLJD+Hx"
    b"cAkC3RVFUff398UKQg4mnAx9CPDjRQqK53nHx8eKohwdHSmKous6C01RFM/zRqMRRRcPjTmk"
    b"VCrFv5VC31vTNF5kzQrGzFBYu91erVb5fH42m3U6nWKxCGWlpFA3aPvpHCErONiNRsP3fVj0"
    b"crlMpVKbzabRaLTbbWQJaBf7cJjMISegAbyt6BZhJERN/eqrr+TwBH9RNUQmEzuAn71OXHy/"
    b"33ddl5UIxArODYJgf7HAE4nEer0m77BUUayg/oyHgFaLxSKbzWLcs4uoUChks1m4eK/XIyjU"
    b"+0wmw5wPmZXL5XzfZ+FXKpV4PO44DuCIV9Rut5Gk6RlZ1+QHCQVeswa56pedvSeKoqiHh4cs"
    b"MZFWUnjCPk4yHEdRlEKh0Gq1eF/WyJs3b9LpNMlPiJnwe3p6AuCBDLrFUqm0Wq2y2Szq5eHh"
    b"YSaTabVa+K/sQgDy6ZCQNHhPSjYzeTRbtMq4cPl8Xtf14XBIW7pkkQAACCNJREFUIti2rWna"
    b"3t4e6uPz8/OHDx/6/X42m221WuPxuFqtappGZnHJ4M8ufwbjgFfBGVWsMK52l1jJ4QHVTJHJ"
    b"stzr9Wq1GurS5eXlarXq9/tff/31Njy0Eo1lPp8zYkn/RdVDn2FQDUBZrVY3Nze0/pybfHNz"
    b"8/btWyosF1ksFpHrOp0OWhidFu23YRjVajWTyWBtUM01TePmocQye8UYi+u6kG16cngMBA2c"
    b"ETqf6E+DnbP0FUVRj46OpB2HWhAz+B7ojspuWZbneQcHB8PhcDQaXV5evn37FvrKtyTi9Ia7"
    b"vbHgAdwMdB7XdXFAUA7++eefQqEwm83Ozs5UVSUEsND7+3tWOu2qZVmWZeVyuVwul0gkqDmm"
    b"aTIJQNZDxIRUx0A/SrFt24RGSDGGYQRBAPyRaPwCq0rQriAI1OPjY7H61C8Na0LO54Eg3Fsa"
    b"WkmSGo3Gjz/+aFkWg4CUAqGgJ5NJGn1gDlUE5R6Ioaej5FM0j46OVFXl+lGTJ5MJAjf9VrFY"
    b"nEwmvEkmk8lkMqPRaDKZrNdr4judTm3bliQJFoIixCgZy61YLBJ6AFQQi90GebtztnIQPmtG"
    b"VVWVukbxovPiAoguRQGyC87xCwcHB4PB4PT0lA5DiEEQAk3Tut1uIpFIp9P9fp9mjZbb9326"
    b"MFEZuQDGub/99ttYLDYajYgvDTBpkkwm0+k0pME0TRDn4eGB1o8JL9d1gcjtdptIJBCwBoMB"
    b"XJqTrT9+/AippgMVfZiQaERlEzGSw1kQ9fDwEEijKBCml53navA6ZqQUjk64rvvDDz8MBoNy"
    b"uYwzTM7jOOzt7eXzeeYQX15e+v0+SA9f7/f7vV4vmUwyC6lp2tXVFYZgpVLpdDosltFoxPRa"
    b"EARsisTgUVWVm9fpdJANkM/W6zUrlM4xGo22220qEj/NZpNOazAYPD8/01ERCJRbeWfkXQll"
    b"K9EzSpKknp6eyrLMvArTqGL6TTQBcvjMCCkUpDOZzPv374vFYrlcRmslEAK5+v1+LpdD3np4"
    b"ePA8r9vtSuHeO6SCRqNh2zZfnQHyDx8+VKtVij1rdjqd0j9Cl6iSmIO4JHSOaNDJZJIVjfm4"
    b"Wq0qlQrTqovFAjkkkUikUilmX03TNAxD0zRwcxe7hbD1RbBOTk5Qbcgp4U6r4WNJgvDRKOCa"
    b"rus446VSSdf1Wq1G80iJ4X2WyyUMo9frNZvNer1umiZRQMB4fHxE9vrjjz8SicSnT5+goD//"
    b"/HMmk8FQYKKbBMTRApXhlo7jwO/j8TiTXPBV1GpMOSZ/GNskyplM5vb2FpyhSjI8QGVAlhGs"
    b"nTUkumhZltWzszPiF+w8ikGINvKXQ24EDp1fUZRut1upVAg3JRmBQZIkXNVsNus4DrnpeR5a"
    b"HdVqPB7jj2CsXlxcHB8fM+qWzWaZzEOr4VuRO4iLpmnSJyPV4tBg/eq6PhgMer1eKpUCyLm6"
    b"fr/fbre32+3Z2Znv+4eHh8PhEANNkiRu8zacuN1lBbsZp56enlL4IBpgHlqPCNZuMxmJRFar"
    b"FYpluVz++++/f/rpJ9Eesih0XZ9MJkA1jJmqj+UBJOOtQcdB6Pl8nk6nsdpVVUVWlyTp+vqa"
    b"eH38+BFDiDLKTAYpwwhcp9PhIimaOD1CL7Esy7bt33//PZFI3N/fHx8fM6uCOURZkEP7XlTD"
    b"XVIl//LLL/yFEo4PJkqmWK6KeJpMEPBrjuO8efPGcZx6vR6Px2m7ABEAmNCwUUAJn3qEY8hQ"
    b"xXg8brVaUOdYLOY4DoCNFSp01FgsRsf78PBAEKHXpVKpXC4bhtFsNiFlp6enqM+NRgPbAs2a"
    b"lGRIwjAMZGVRpgeDAdyYgXaCK1j78+7enYuLC1RNdeexKcRLrER+eH0vfFCNqqq6rufz+Vqt"
    b"BuHu9Xqr1co0TT4VBGEASpZlTdNAdFVVJ5OJ67oPDw/pdPr+/j6VSjmOg79bKpWorWAWky2d"
    b"Tmc6nQLJbIlhfnm5XE4mE3gDIe50OrSQpVIJ+Yg6zk4IgUSPj483NzeapjENu91uB4OB0FcE"
    b"SZLDJy58xqzT09Ng54F1Ii4EdbfHVsJJcfrYer3O1KzjOJIkMVfEbATfbLszqIWSqapqv99H"
    b"5zUM4+rqinkAWZbj8Xgmk2GYy3XdzWbz9PS0XC7n8zllFHFN1/XRaIQsQxZDwdGz6B+KxSL3"
    b"ibZ5PB7PZjMSNpvNTqdTz/PwgYIgoPFCO/lM01X1JXxIh1hSn3vB8/Pz/4TpXzwLx83F/5LD"
    b"kUlJklzX/f7777/55htZlukVEPagPMlkkqYHekny9no9sH84HLI6ttttoVCwbTuTySDLBEGQ"
    b"TqfZDEOBkySp1WrJslypVKLR6Lt376gS6DwvO89T4q5ATZj+SCaTpVKpUChsNhsYrOM4BwcH"
    b"V1dXZ2dnf/75J1QjCOfZuGqhU5Fo4v3/T7D4r3CGg/CpXOIPmqadn58fHR1ZliWm1TFfdxsU"
    b"dsNQkjqdDujALoy9vb12u12v129vbxkta7fbWKT5fJ7vHY/Hh8Mhc1hsHpJl+eTkpNlsdrtd"
    b"ODotFFwUvZS9ZAhk2Wx2sViMx2M01f39/XK5zMTdyckJHe52uwWtIuFGAQFEcvggI8yhLzJL"
    b"5JQUOrREnbJFjdA0DYGl1+t99913hUKhXq+vVivEP2GasoPFtm120VGMWq1WEASu6+ZyuYeH"
    b"h1gsxow3l5TNZg8PDxHIZVkGzvv9PtuQQatMJgNyw9GRD2VZxqdYLBaM21H4qEJcAsAHPGFc"
    b"c/6VGL8CKwRqb8On6kg7QrOqqv8DjxomFsSpzQwAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_administrative_tools_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAXWSURBVGhD1ZllqC1VGIaPjV2YYNdV"
    b"FMQuFDHwly02Jooo6g8xMFDEThT7h3FtMLFFQcTEwBY7sTuw9XnG/XHXnTNr9szes8/lvPBw"
    b"zqy9Zvb6zqz11RnrWHfDvxX8BFvDpNA88A9UGSJXwKTQOuCCXyyupmkTcPzJ4moSaG9wwTcU"
    b"V9M0Pzj+I8zkwIzS6nAcLFxc5XUGuGDnlvUh+NlyxVVeG8BRMFdx1aHcLt+Bi/gEtoCc7gTn"
    b"bVdcTa97wM+2La7Ga1Y4Bf4C5z0MnRmTGvF57+ffcDbMDqkWgPfAOSs5UFK8rfNgZgcSLQtP"
    b"gJ//CV/3fu/EmNSIm2E2OBb+6I09D1NgU7gDfgPHv4dZoKydwc/FN3sqLAq7gfc4/j5sDCvD"
    b"p72xoYxxgWHEjZAubG14E/wstoE4fypsBFVy6xwKeq5w0b/3fspNoFMIpcbcDwM5iYPBB3wL"
    b"czpQ0txwJTjnAzgI5oCmWh6uBreRgXJfqNJe4Hc4bz4H2srFvwY+xPOQ0zLglhtUS8Fi//86"
    b"Ti7creYadAIDyy3kefBwb+7ABMs3phHPgNtyKB0PPuwjWNCBCdKO4Pf+DJ6VoeUh93D6UD3X"
    b"RGhxCPfr2etMK0B4pxUdaKAlQXd7OBwIW0JTZ3AO+F0PQKfpjIvwwe9Cv71qevEIeK68J8U8"
    b"61zol+bsCs43TnUqA5IPzrnIkMEyDPgBbofz4VJ4GuKzj0FHkpNR/1Vwbl061EpuERfwFdS9"
    b"DY3wi/X3J0JVJF4N4o9iJDfo5hRx7JriqqUsitaFfeBMuAv0Vj7wKshpfTBSe462caBGOg+j"
    b"v898qXddpUXA5xn5nwUNOgZMOD2nufvGboNcZWd0r9sKngnnnVRc9ZfJZgRb65ecLod0HSm/"
    b"wu4wTjHhBbgerCdMxWutR7H1PBNtErs9we/TM9VpXlgP9gczDEsBE07vLRdvhcKQttoJvM/s"
    b"t42iYjTgtdUe0LkhR4D36Z3aSgfivW2TwZEYcgB4ny62rdzn3lsu0PqpkSEWNWlN0E/6ee97"
    b"qrhqrlXA+4wpbWQleTpkDXGvhjFi+myjzZs89LkDb9phxPbAr+pAQ50Gfk9dn8sS4TBwjvme"
    b"DiVdo15tnLYCb/Ava6GT3iDGlpw8H84x2NV5uJCB8RfQ+DUdyOh1KK/DuHYv+IfQY9bKRM0K"
    b"bnu4CHzAg5DTQuAWcd51UJcc+taiQXGZAxkZt5zzJfhWNoOhygjTki/AAitXySkbFdFAMNhZ"
    b"opbrb7sovgnnvA0bgguuIspoA3XV5yk2MBop0mrbOHUyd3oZnBtYV4R3GhVmJBdCXy0B5j0u"
    b"qJ9HM3P1bRixUwfi1rN0jTTIPMszNSyPQrShrCprZfruRHOuNq5ZmWLEmVkDfM5nYI3TFVHb"
    b"XwBZWR3qXp1owTOMoiM/KrJB2YNuQeQkvdGwCkNs5FVtk0F5A2oNsaXpBEtct8iwCkMeL67q"
    b"ZdOhX0kcOgSyhlh7e8BFN1klA5KNs6Y9r6aG+EznPQflZneVag05GvxQ91nVV7JD8g04Rx4D"
    b"U/q6mqTKEANkutgwwj9gZeFUoVpDXJD7zwk2kk3ylCn3teC43AfvJNcGPONOlcqG6MUMojYp"
    b"bNGmRlh4NVWtIapsjPEherF6sv1AmV/pw43CLsJYYf1flvV8aoiGRU0SKU5bI1RfQ1RqTGBi"
    b"qVuuUkR2mxhlRfs13VqW0m+B46kRR0JdSpSqkSFKY0wabfWcDHVtIf+X4kOrsmW3UNkQZdJp"
    b"hPaNq0iJ/M/w0Ie9Sk1K0hPAh55VXE2vaC2lhqwFbs1ojYYRJqk6jyZqbUgT7QA+1G5HKreJ"
    b"46khdkd0DjoM49QgRqiRGBIlrC2bXRLCI6WGeI7Muxyz7vBnWyPUSAxxm/RL29OttTS8Ao4P"
    b"YoQaiSHK5PIWuLXEQ1A2RJlRuxUNsoNoZIbk1CbXaqMZZohlrklhV9gWmlBDPNx+4ai4GCZE"
    b"OgI79raduuaSsbGxKf8Badt0RMmhpAUAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_play_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAFKSURBVGhD7dm/KsVxGMfxX4pBNjLJ"
    b"qpTNYDqDhUuQO1DcgMEVWIwGC5egcwVyATLLjAUpSf68H3zrk4iDzu/7PJ53veo426fw/Z3v"
    b"abIsy7KspbYx/vrSd5e4wPLLT46zIU9vupiEy3SIucYqBuCq90OKQ0zDTTrkRl6bO2xgCNWn"
    b"QzrYwaO8Z44xh6rTITP2Bs3jBDrmAVsYQZV9NMQaxibuoYNOsYjq+mxIaRZH0DFmD2Oopq+G"
    b"WINYxy10zDmqOUi/M6Q0hQPoGFPFQdrLEMsOyhVcQcfYQbqG1g7SXoeUJrAPHWNaO0h/OqS0"
    b"hDPomFYO0t8OsUaxCx1j+nqQ/sWQ0gLsnNExfTtIc4gU4lfL/R+7+3+/IQ5E948oIR4a3T/G"
    b"h/hg5f6jbpjLhzDXQcr1BZ0JcWXq/hI7xNcKYb7oybIsy/57TfMMeVT4gW4EYDcAAAAASUVO"
    b"RK5CYII="
)

# ----------------------------------------------------------------------
icons8_pause_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAB2SURBVGhD7dnBCcNADETRrSrFpI8U"
    b"k3pSWGzBuACTAQfzHuiyIME/7wIAfvfY5515zcNJs3Psz63LPPf5Zj7zcNLsHPtz6zJCQkib"
    b"kBDSJiSEtAkJIW1CQkibkBDSJiSEtAkJIW1CQkibkPibkNt8KwDADay1AZozwcm8F5lJAAAA"
    b"AElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_lock_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAGGSURBVGhD7ZXBKkVRFIZvMeAJJHkB"
    b"JSVlIgOKKIw8gkxkes0ljyAPYCJRUjIykJmRIVOlKDGgUPj+Oqu0w3G3e/Y5buurr07rnL32"
    b"+m93n1NzHKc0OrEPx3Esu+7Af8Mc7uEjvgeqtouzWFn0i59iOPx3nqDWVIppfMBw2Ce8zNR1"
    b"eP8ep7ASjOIz2nBvuIM6F+1o6FrnRX8tPWPPa+0Ilko33qANdYcTmMck6llbpx5dWBqbaMPo"
    b"IA/gbxnEzy+EDSyFXnxFG2QBG2URbb169WByltGGuMA2bBSdG70IrM8SJucAbYBVFSJZQ+uz"
    b"r0JqztEGmFEhEn0crY96JucWbYAhFSLRWuujt1dy9DGzAfpViERrrY96JseDBHiQGPTN2A58"
    b"QRvgKKvFqLXWRz3D+9q7aWyhbZZa7d00WjLIMdYL9hALD7KuQsGsoAf5CQ8SiQfJw4NE4kHy"
    b"8CCReJA8PEgkHiQPDxKJB8mjJYNc41nBXmHhQVLrQb5iGOdLUns7jvMnarUPpRqxAEGuZ3QA"
    b"AAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_move_32 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAADiSURBVFhH7ZUBDsIgEAT5hH/U6HP9"
    b"T+1GNtlcSuEKHIlxkoukhduxVkh/OrnlWgKC37nCJRi+5QqVsOGhEhpun0CIxGsvDaKAimHO"
    b"VB578VtSAOAa7oWiAkuYKoBHev8Oi7QIoAd/smb0pXriwkWwFj1c/w4Ndy08wN1rZDhp7qkT"
    b"a1XiaK6tosRyAaASpxMduHuOlLjcSxee7e24jyphzw4XWFDb22sCQM+O4bQITGWJgO7tKoBr"
    b"tbOjG7u3UwBjvrQ9Z0cVDeKnjik2FZXQCgknViI0nFBiSThB8LLwXyClD9l3kJtafbLiAAAA"
    b"AElFTkSuQmCC"
)

icons8_move_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"zUlEQVRoge2Z7U7CMBSGnxhN9I8OZEPh/u8AE2OiIVFQgciHIsLN4I+2aZ0BaffRzfRJmmwj"
    b"63lfoO1pDwQCtSWSrdZEwCvwBlx61uJMBIyArWxTamimAYzRJkwzLY+6rGgBM4TwL7QJdT2j"
    b"BmZiYI4W3kEbaQMf8voTuPKk8SDU32mJFqqMIJ8t5f2odHUWvAATIDGemUaQn02A5xJ15ULa"
    b"SCEcFR2gLIKRqhGMVI1/Y+S4hBhPlDD9HkIMPAI9D7F7iAwgztpRC507DbN25sBQxl6QIdGM"
    b"EKmESgCvc5FmRwy8Sw1zHMxE6ARwjR8TigSdNc+w2JxdoHd2a0Qq7ps2OmueAs2/XkhvT22a"
    b"y2Rw4xhrTOpAI72OnABnDoIAzkt6B+AUoXUvmQdYAThPPM4DrAAyTzwJlgOsAMyJZ0OGiaeD"
    b"+Ba2QD8PZZb0ycGEoov4ZQZZO3JgIGN3PcT+xR1w61tEHoTDBxuCkaoRjFSNYGQHPeABUejZ"
    b"RQO4p+Jri9rfT9C5mbmONNFZ7KJ0dRaY9Q9VZlNGzHLchoqkHfvo8LPMtk1dq0pWLTDLbGar"
    b"lQlFgt5pboEVNTShSBCDeoXfI6VciMnhyDMQ8MQ3mEmjvi1225cAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_route_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAHQSURBVGhD7dZJTgMxFIThHIIlK2Zu"
    b"wIYdO7ZwAeZZnDV7FszcATFUCT/JMk7Hr+12/KT+pRJR6LjzKSCYjI3Z7cjNdAR8uZnFCOLH"
    b"zSQmRJjEhIgPN1OYGGLbzQxmFkIygZmHkJrGpCKkJjFahNQUpi9CagKTi5AWiimFkPjad6wq"
    b"pjRCqoophTh0X8OqYEp+Eo/Y/d/Dfw2KKYlghPCcqpjSCCYQrgpGg1jGVhL3ismZ3KAY7Scx"
    b"xeTaPhsEo0WwXMgntobF6oXpg2A5ECIOsK7UmBKQfT7Rkf/LnoJgW1j2p8IDND9aqZBBERIv"
    b"/MbkxTyIB85KC9Eg3jA5m+8pGSFpMBrIA5aC2MSyEdIx5mN4MG8QpoHsuq9dxRB8L1mlYDSQ"
    b"efFs/49mEYR0gvkY3sjH7GB7bkt8omcbWIjgvYt2ioUY3rhUMQTvOUhDYXjGC1YFIZ1hPoZv"
    b"IAezjoUI3qNK51iI4RvSFkPw7KqFmGdMg+G1fM1CEdIFFmJm/Rfrx2tCBM9aaJeYBhND8Iwm"
    b"imFWsTA+1yxCusK6MDEEX9Nk15iPecII4PjYR/DapothzCGkG8zH+Ah+z1S3mI/hYz5nMsGY"
    b"Rkh3bmNj9ppMfgF/kbj+SZ89mgAAAABJRU5ErkJggg=="
)

icons8_resize_horizontal_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAECSURBVGhD7dhZDoJAEIRhzuNyKJcH"
    b"vYnn8VjewaWbUMkEDRGmu2lI/UmFt2G+RF9oGGOMMcbaNt3TMo8zB7vInt3TKo8zB9MXvWTv"
    b"7nmU1XaWlWe6Y0qE7iHbymrbyfQsnOuK8UKgEIw3ArliohDIBRONQKaYuRDIBPMLoQdHV4XJ"
    b"gkCTMNkQaBQmKwL9hbnKSoTuLrslm96pvKPeWe/edpD1EUua3l0N64Foq/hpoT5mCX/2LwTK"
    b"ihmFQNkwkxAoC6YKgebGmCDQXJi9zAyBojEuCBSFcUUgb0wIAnlhQhGoxOjT4gPdSVae6Y5A"
    b"+iLrz5s4MwyBVvERmzHGGGP5apoPcwpl40zo9wQAAAAASUVORK5CYII="
)

icons8_resize_vertical_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAFSSURBVGhD7doxTsNAEIVhi3NwmECB"
    b"aJLj5VQUUHOOFFTJPMlPWq1md8aRbM+Y/aUnnBRxvm4NTKNR3j7mpe4i+5uH65QRcZ+XElMj"
    b"UmLOMg3BpcBYCC40pkbcZF/Fa1zjPb4OidEQb7Jr8R6u8V5YTAuBaggKidEQJxnTICgUxkKg"
    b"FgSFwHgQqAdBu2K8CGRB0C4YHP68COSBIA3zKVutV9mvzINAXggqMbgH7rVquMGPzEKgJRAE"
    b"zLdsdQR7mX9aLYUg72dv2jOQkA1ItAYkWgMSrQGJVnjIIY4oPDTigGe1FPIuw2dvcvItj/EW"
    b"ZgkEiM2O8dqDVQ/jhZTPItjqD1ao9+ufOg9EQ+z63K5hLMiuCObB9CAhEMzCtCChEKyH0SAh"
    b"EayFqSGhEUzDpPuzAqsxrYVGMAuTAsHwRTVMKgSrMSkRjJjUCHaIf+EY/dOm6QETlEg8SIvm"
    b"sQAAAABJRU5ErkJggg=="
)

icons8_save_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"XElEQVRoge2YS1ICMRBAn5aFx9E1eD0/HEV3bLwAehOHjZ5BXBBKoDLm051Jl/SrSg1Uejp5"
    b"hGSgwXGcUmbAEtgA207tOcxDxFNHgcO2ksoMIdF8pH8/UAv2ub9QkElNdAqRG+AzvH4FriXJ"
    b"avtTvHP8FVqP5L5FuDKtRWL7YSy3aGWmEonliuWulrEmApUyFkXgeM+8lA5U01+Sv0QEdjJb"
    b"4Lt0oJr+kvylIqMxl4IJSVF9FvUQeTt5v45GKWDhyV4cU7Mim3BdVNz7F3fhOmglTH0qjwcx"
    b"Ldq9cH7ZgbMgM6Ar8BEkUr+p1ER6Y+74VcVFrHHWIi2rLAO7E1FcQYH0qTVFleVBML/swFSV"
    b"RcKC35UZQ02k9XOmavyz3uwmcRFruIg1XMQaLmKNHJHef32zxv83K3KVEXPRfBYK48dWpFUB"
    b"ToOiIl7rApxGSxXxgHYFOI2WW8RzHOeEH/58jcLJRDukAAAAAElFTkSuQmCC"
)

icons8_plus_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"yElEQVRoge3az29VRRQH8E+18h4Bhb5aYCnxJ2gqe4I/FmoRF2iiiYo7DG74EXSr/g8mTfxH"
    b"DBGjCKKxiigbawHdqCSaYOOvCkHzWMxM5tb0te++N30tCd/k5iR3Zs6PO3POnDlzuYnVhaGC"
    b"vFp4BDuxHXdjE9bF9r/xC37AtziNU5gtqEPPaOIVHMd/aNd8/sX72IfGgHUHa/E6LlWUuoKP"
    b"8Cb2YhtGcFt8RuK7vXgLJ+KYNP5nHBU+zkCwB99XFPgS+7GhB14b8SrOVPhdxO4imnZAE+9W"
    b"BH6FJwvyn8DXFf6TlmF2tgiKtwWnPYhbSwuJPA9jTp7tzaWYbxWmu41pPFSK8SIYx0yUeSHq"
    b"0BfGKgy/wJ39MqyBESFEtwWf3NIro6a8nD6T94NBYh0+l5dZTz6THHta2OxWCqPyqpisO3iP"
    b"7NiD8ImlMC4HgIluB62V94mDBZRI4bRfHJGdv6sl9oa8T5QIsaUMGcY3kdeRpTo3hFShjScK"
    b"CKecIfB05HXJErOyT44QpVDSkCE5kr60WMcPYqf9hQRT1hA4EPkd69ShJaTVV/SWAHZCaUNG"
    b"cBXXVPS8pdLhUcG5P8XvBQWXxqywSQ4LBznMN2RnpB8PTqeecSLSXelF1ZBtkZ4bmDq9I+n4"
    b"QHpRNeTeSC8MTJ3ecT7S+xZqvCw4Zem8qrSzE7LwNn5dqPFqbFzTBaO6RYa6z1JoyHUCzF9a"
    b"NzSqhvwV6fouxg3VePoZ0wl3RPrHQoZcjrTYGXkZsSnS39KLqiEpWi0YCVYZ7o80Ra95hkxH"
    b"+vDA1Okd45F+l15UDTkd6WOD0qYPPB7pqYUaR+SkcWNBoaX3kZacNCannzcjs/hQiNHPFxRc"
    b"Gi8Ie91xlaj1f7wsfL0zBQWXPlidjfxeXKxjAz/Fjk8VEl7SkGcirx91cQ1xNHY+a/UVH85F"
    b"Xoe6GdCUa72HCyhQypD0gWfUuBTaHQfNyTF7JbED/wg61b7KmJS/wGhZvWphTMg62ninFwZN"
    b"oSzUFs7IK1HEXo+pqMOUPu4Zx4Q0IF0rjJXQrku0hEJIuo7rO5ndKk/tjMHkYjsqMs/jrlKM"
    b"N8vLbE6ovQ6XYl7BsBCdkmNPySl7MTTlANAWCsqlbl+HhKuMtE8kx17Wu/cJedpT1f6AkHTW"
    b"RQuvyWlHWkolb4sXRVNYXimdaQsZ6Um8jWfxoBC218RnVLg0ei72OSkXPFLaccgK/QHREKri"
    b"x4QjQN1qyTW8JySAfRlQ8qeaDUItdpdQtbxHCNe3x/Y/hTrURSGkfyLMSsdU/CZuZFwHvZQq"
    b"HNfefn4AAAAASUVORK5CYII="
)

icons8_trash_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAFwSURBVGhD7ZmtSgVRFIVHBDEIahMU"
    b"X0AFg8EgWHwEQRCsPoAWq8Fg1SCCVYuCJvEHk8VkEGwWX8AsFl0L9oaDHPHOZZ87w2V98JXF"
    b"MPssmDn3cqYSQggBpuEBvIH3Ge/gMZyFrWUSfsDvDvyE87CV7MHcov/yDLaSS+iLPIWbGQ+h"
    b"X/MMe8oAHO/AW+iL3Lbst2vQr3m17D8HYQij0Ic34RwMQUWCDCvi78gu9JufWxZtbkbYO+Ls"
    b"QB/CXakEvZihInVotMgYXDGXGCR4TocZGAvQ8wkGRqNFuHjP3xkkeE75h9J5hJ6vMzBUpA4q"
    b"YqpINCpiqkg0KmKqSDQqYqpINCpitr7IIuSZL31hkOA5nWJgXEPPVxkYjRaJREXq0DdFeDDt"
    b"Qx4YFOAE+gye3BdhGfoQegRznw66dR9+Qb//BiwCj06fYFqmlG8wPT4Kh1sot9jc8Cj5WzQD"
    b"izME+ShcwNwHz269gltwBAohRF9SVT/YcCJDemJ9EwAAAABJRU5ErkJggg=="
)

icons8_manager_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"60lEQVRoge3ZXYhVVRQH8N+MqZWplRA1RoaZ9IWFBUX2RfSBD4VFEdWLwWCYZS9F9RAGRQV9"
    b"GSRU0EtBgVFUmMQYvuijEVlWMAZJmYTgV1oONjM9rDvMvqdzzz3ee+begvnDgnPP3mvv///s"
    b"vddee18mMYn/HfrxPi7tNpF2MAt/YBQfdplLacxEX+15Dh7DoBAxZhtxN3pr9c5HT2dpFmMm"
    b"duJPfISD6gVk7Qdsrj2/0QW+DdEnRBSRb2SbqiRyQpv+v+EL3JG8G8UGDGAf5uM+XJjxfafN"
    b"vivFHPXTaS+uy6k3BWvUj8jHHeJYCo8bJzYiX0SKdZn6504kubKYpT46fZYpn4tbMT15dzqO"
    b"Jj6v63L06sch9VPl4aR8Lg7U3n+e8d2S8duJBe0S6m1eJRc3itCb4kDyfAlm156XZOrtz/w+"
    b"r1a/K1gkduz0yz6dlE8XI3EAqzO+OxKf/XgRp0ww36bYaJzU9yI6FWGxevHLc+pcgF14QozW"
    b"fPExdmFhFaTzcFeG2JqCuifjq6TuQczIqXdnps3UbqqKeBZTRNqRdrZORKcUi9WLGMVzOe0t"
    b"wG6Nhfwi8rQJwVjulNpRbMWn+K4BqZVJG1dhLX4tEDFmv+MtXFmliIUlOm5kXyftrM0p3yim"
    b"0s0iDcqWv1qlkB6RxQ7gHpF2jDQgfkhMp5U1EcuSdqbhp6TudkxNyqeqj3a7cVKVQvIwT+zY"
    b"aYhdLn9hp9iW+LycU/5aUr6tIq5N0SN27FGxT5RB+sU/ySnfoAtCiAi0TLnNrl/9lBzBilpZ"
    b"j5iOafnf8vegrmOVmILZdbWvZum7EbFGVrXS0RQsxXvYgyExFZ7BWW0IyOJBDGsc6YbxQCsN"
    b"XybC3J6CxoeEwCvaUZBgdUFfTx5PQ3PFgWl7QYONbItIW9o5Ql9da2tA5FtPic11FNeUbeR5"
    b"sZBa3eTG7GfxMU5tUcwS9eF6hn8fBwqxvgIRqf2Fd3Fxi4JaRtVC0kizCbfp0NF2ooSktkNE"
    b"pxOPk1uPONDdUsa3E0LGbBBnlhAwG4+oPy4MahL2OylkFC8UcFmEN41fhhf6tnvT2C5Oy/ye"
    b"Jk6ID+HaJr7Zw1sdOjkix4yH1LPxrOKNN+tbuKd0Ssh+kerfL27xjx2H77e4oUhEJ4W0Ynvx"
    b"qAbLoewaOYgPxDmgD7erLrdqhiN4BS/hcFmn7IgMinwnL9W4XFwCHDYxIzBc4zOvLPk8IVvF"
    b"X2XNLtyIy+wV+KZCEV+KzLtl3IuL2vC/XkzBoRJkGy3kpW30XznOEFMyvRlpeSH/F9Ar7qbW"
    b"yw+xR8TlxKxuEWwF54h7rR/FHdfb4hA3iUlMYhLl8Q8zzJ/A80nLpwAAAABJRU5ErkJggg=="
)

icons8_center_of_gravity_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAKRSURBVGhD7ZpLbtUwFIavQCp7AKmw"
    b"gjKAYWnZC6LlsQHGjJjx6GOIugr6WEQLzHirSygSApUB/F97j3SUJre2414nt/mlTzdNcmyf"
    b"xD4+djoaNKifei6+jeG4t9oU/8Zw3FsNjnRJV8WWMEc45lznRSPvizfivfgjzAmDc1zjnmXR"
    b"Kceuicfih6g2/Dy+ixUxJ4qKp/pV1DUyhi9iSRTRdXEkfIOOxTvxSNwRb4Vd45hzXNsW3Ott"
    b"KYsyi4g38kv8Fa/FvPCaFLVuCsYKtpRBWUVFl1g4PTyjkPCL7dS71Y3xb6hCHGlSbF3B4tX/"
    b"HP+GKtUR6mDMLJ78lVGEWItO9Od7IkQpjlA2dWDzWWQNzUQaaxDRpmlMVJXiyG1BADC7VZFF"
    b"zL5MXFYw0SlUKY6gdWF2LAGuiNYi7bBCeVLVEDtJqY5Qh38rWUIzsd4KZCKLUaojaEeY7StO"
    b"tNVHYQXG9tc2jjwRZkui2UqMD5/FkmLEqI0j1GW2v0VUpvxMvHD4QQcMdH/9PPaF2XJcd08T"
    b"1OXrpi3+Om1t1KHwxl2GtjZqZhyZma5VVcnBfleYbfRgr9MHYQWSqsSojSNZwy8qNSHuCbN9"
    b"yYm2KpGisHr0KUqWhVc1aVwToUp1ZEOYHcuHLEkjIjWxgnlSpNohSnGkmsY/FNnE4oZFDgX3"
    b"emGFWHay/Oz1Utc0zc2Hqe9xtd0OYkwU22U00QXozwxOohlh02uSI7cE0QlbysiyCkxR3ZYp"
    b"jdoVbGqTYlS3TDn3VHCPj0xQdMuULsEGtG9QCp9EaCS8MBEe+TTgJ81QmOweiOKfFbzIAOjn"
    b"pN8HoulDD+k8uRNvINuMfZHCsV5+eqtTSPjthQZHuqaZ+ReOQZdUo9F/xyvWUiCu12cAAAAA"
    b"SUVORK5CYII="
)

icons8_delete_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"bklEQVRoge2ZsW7CMBCGv3aAEdSRvEkbpLIUHh2G9l0oZaYDtkBRCPH5bJ8if5I3uD8f+BzL"
    b"hkqlUpkqc2ALNBmyGmAHzLQLL4EDcAGOQKsdcEfrMi4uc6lVeMFNwo8/4FMr4I4P4LeT9QO8"
    b"xRbuk0gl0yehIjPnsYQfJ3SmWetqDWUdEPbM7klhLZkxEn5sJQENt6YbI7MWZKwDJI7ASiIC"
    b"8M7jedvXM5uA2kM9kaQfQ2TOI2WyS6SQKSahKVNcQkPGjESMjDkJT8iyeQr8rGQZjyLkVzb3"
    b"T3TRkikq4YmVMSHhkcqYkvCEyqhKvGoVEvDihimkU2vs3iwLsc1uQkZr+S0qo/1CLCIziS2K"
    b"ZAMY8p0zGd4tMbtYMztgjQcpLqP5AMVkUgRnl0kZmE1mMgd0Fo9MvyQB1g6x90Rc/CxcgRzL"
    b"49DpzDdKdyRdmVQvrD4ZFQnPJK7ePDOu9xPio/0AVlwbW/0ytFKpVGzwD150jA21lxWtAAAA"
    b"AElFTkSuQmCC"
)

icons8_goal_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"vElEQVRoge2a329URRTHP7ttY+VXy4PUmhCNNj4QoCXRBLUSrZBY22CKMaGAkb+gShA1URIF"
    b"bE1DouEPsGhgK30ioomJTXyAqqE8+SNqVaS/7LZoKNQHpNr6cO5lz5yd3Xv3R996kknm3u/M"
    b"mfneOefMmdmFZVmWJZFEmfUlgU3ARuBB4G5gVYD9DUwDI8D3wLfAQpnHL0kqgXagH/gTWIxZ"
    b"/gLOADuBqqWa3EvALPA5UBu86wcuA1tN200FEvCVSeAAsLLcRK6pQS4GZBaC5+seMltMn3lg"
    b"HBgGPgPOAoOIWc3nITQOPF9OIp+YAS6a5+vAI6ZPK3ACMZU1eXTfAWwDjiEr7CM0EKEjttR6"
    b"Jm+Lj0yhkkA+wJBH/wjQUKJ+IB6Zq8C6cgwGdAJpoz8NNJWiNEXGJ6LKYdUvCbQA3cB54Dck"
    b"7N5CQu/XwHHgcaDCM24d4kuWTNErk8t2faXfEInbbxp4Fag2Y1cCfabtCEX6zFbEB+JMaMD0"
    b"jbuSYRkDdhkdCQ+Zj4shAuLIcchYIl3AFHAKeA14EdgPvAF8gKyE1bEAHMXNNCrJNrPnlpLM"
    b"j2Q2zThSgfjRBY+uFGKeodThBoAxYEUpZK5GkBkukEwou4E5o+uoabPH4C/HVV6JpB1a1iHR"
    b"KYWY0gCyElFkksDTwDNIIpkkWzYjX1qbWYfCE8BXCp8gZm7WjuROWyLa1QaTjyLTRSYA/AH0"
    b"AGs9ZPTKjOJGszYzTnscIv1B42vI1yw3mTD0Nps2nUbPKwpLAFcUlooikcTNZE8YzHd+KZbM"
    b"TQ8ZnaqkcU2xR2FX8ZvpbWk0E9qpsBYyNtxVJjJp02a70fGYwp4w2OZ8RPaqhvO4u2m3wqY8"
    b"feOSOWTadCusAphRWK/CqoF/FbY3H5EjquGYwc4r7FSO/nHJnFP4JK7JnlTYkOn3q8Le1oC1"
    b"s7tUfcZg96j6d6quk79ZYAdwSb17CPgCqFHv3jN6N6jnX1T9ATOH8RxzzSKyWtUtkTpVn1b1"
    b"7bg+k4vM6+p52Oher+rabO1K3lB1J4nM5/m3zLPehBKm/j7RZCrzjFWyWOVzqr7aYLNkDlH1"
    b"6v0EGTKQCdmzyGodQhz1HdXnYaNbm4w24VnTTq/CDfKIdvYRg+k0oU+9TyI7dq7Q7JNPye3s"
    b"Hyrsgumnnf2tfAPsUw3nkYuCUI4rbBrXyfVmtYCsQi55Ezeq6ZUqJPzuyUekyQyyTWHNBntK"
    b"YWvJPmecQzbRVUFpwV2JcD/S0WyHwR9V2JMGs4mtI0nkBjBsfExhFWaydtmbkbRjMWa5aSZq"
    b"s9wp3GD0rsJmiHHde0Z1uGw62F15t4eMvQnxlSnc9APcrGIROKiwJG7SeDqKBEh+pRW2Kqwa"
    b"SbFDbI7snKcWSTsmPQQmEZ+oMX0akduWsN3vuP7ZbvS0xSFSZSZh04QO3MRvzEMGZCU3IB+i"
    b"Naj7zKERCb86WDxr9Hyj8HEK2JMO4H6BToMfMficp02UJBBz0ivhC6v7DB4nvN+WlbhfKY2b"
    b"oiSQw401nSEkmvku30KpQKKTdmxt+3rV6nEDzChwZyFEQG7F9SCDuEuaQFbGd481g2yah5Gr"
    b"oP1B/ST+i4wFJJvVJKqAL007fZYvSAaMoj6y7bwDNwAUWq7g+gTBGB+ZdpHH23xSg6Qqlox1"
    b"tmrkjB0n9OoQfBA3OoGshCXxE9m5X8HS4JngIK7PhJJE9odexF/SwD9BSQfveoM2vsy7nmxz"
    b"mgLuL5VEKE0eMmki8p0CJAG8QHaaM0XE2bwYaSDbzBaR6NNGcb8QJ5HNTu8T2pzKthJW1iC3"
    b"4rmcthu57bA/FWipRhLAHnIHiRQF+kSxv7PvQg5S63Pg/yHERpENDyQDvhe4j9z7zBjyi/LZ"
    b"IudVlKxALpQnKD706rSjiyI2u3JK+IeBFNG39nbTPI34V8nn+aX4C8dG/H/hmEOi0s/AD8iV"
    b"0mKZx1+WZSm3/A9x0g4/FKsS0gAAAABJRU5ErkJggg=="
)

icons8_file_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"R0lEQVRoge3asU7CQBjA8b/GTiZOjq2Y6DsQnsVBjAuPwOAD6FM4uTj5BCjREN6C0Jm1mwaG"
    b"c7gO9E76nfcN3z9pQqFc75emoWkBy0rSUeR2BXAPDIFTgf1ugEegFhgrugL4ArbCSw1c/aOD"
    b"SQKEOOY4YpuhxI681t7rCnhHABMDkTgn/KbAi7deAR/AdZ9BYyDS/QC3tDEl7sgcjMkBgQSY"
    b"XBAQxuSEgCAmNwSEMBogIIDRAgGHGQOv3nslMAMuQl/OAbns+OwbuKGNqXC/PZ2d9JvTQT3g"
    b"LlZXHdu84a4oBr/r56FBc0DOgCfpQTWdI70yiLYMoi2DaMsg2jKItgyiLYNoyyDaMoi2DKIt"
    b"g2jLINqKgTTJZxEuOIcYyFJgIn1bSAxSAJ+ke9YeWuZE3KP+y1847oAR8o+r99XgjsQz7nGD"
    b"ZeVoB0LBdk/cOVz+AAAAAElFTkSuQmCC"
)

icons8_file_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"qElEQVQ4je3VMQ4BQRSA4Y+o6NxBsfXWWyhU7uFOtA6gYhOtwhEUSoWKQkKt2Y2xwSw68SeT"
    b"vJc3+eclLzPTcKONRJwtTs+KrSBOMMXqhSxBBwMcYyenGEf2jDDDGt1Yh3XJscMCQxy+FZZS"
    b"mFelnwizIN5jib5iUM03ZSv3Q8txRu/TDjfFCknD5N0Oo/yFf+FPCqtXLxN/E6tkmJRJIyjU"
    b"/QIescEFrkM5GgOS//FxAAAAAElFTkSuQmCC"
)

icons8_vector_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"yklEQVRoge2YS0oDQRCGv4TgCURBAxp3egdd6BkiIngCEQSXwYXiYiKeQpc+Alm5EK/gKYwS"
    b"Nz52URMXXWPCMEPPo2cSQn3QTDJ0/39Vd9e8QFEURVHSU3KsNxiXf9mV0Lip5KRrm+mkK2el"
    b"DMwATaADvAHn5JegCyrABSbWZ8DD5ICHmaHR5qU08ce76hdGk5B4S5isFlKKRlH01upMTbGX"
    b"gauQ8x5mVm1tGWg7iKMNLMX0bIaMvwRTKB5mi3WlY5xirwNfmG3yCZyQvEZOZexAtOoxxlYw"
    b"F6QugWJPwzHQlwBugNlAgDZG+80Bd/K/L9qF0BDTH2A/IsC4bZQD4FfON3KK/Z9tMfqW30Gy"
    b"JAKwg5mgQYS+E2rAu5gc5mUCHInHB7CSh0GLYU3kjV8zLdfCGwxnadG1eAhVhlfEdZfCtyJ6"
    b"5lLUgv/odO1KcB5T3D2KWQ2fqnj2MJfozOxhZubBhVhCHsV719YxzrPWphzvs0SUEt9zy9Yx"
    b"TiJrcnxKHU56fM9VF2KvmOWtuRBLyIp4v9g6Bt8bxvbxIKv/1LyPRD2uF/7xIKv/1KyIJjJp"
    b"aCKThiYyaUTdR/K+T9hI7D81K6IoiqIoCvAH9xeE5oCkha8AAAAASUVORK5CYII="
)

icons8_vector_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"JElEQVQ4je3SvUpDQRCG4ScmNooK/tQBCzsbTWOhtSAiURCsLIR4D2qrhZdgITbiNVgrCBIr"
    b"i4AIxkYQgiEIaQSxcENO1kMSsBNfOLDz7Tezs7OHfyKKKEdfsVtCFmvYxA0+o/0l3GEXJ0Eb"
    b"DlqSQRxgLIMGRvGA98g4iaNEsRL2UIt8I5hBI4djFLCDt2CYxhnqKbeqo4ltPAVtHKe4TfHL"
    b"4x5zoaOq9vyqQZsPnnxagZjrkNCLQvB2kI3iZUxoz6wbL1jABx5b4kBkWsV5H8VaXGAlrcN1"
    b"LGILr5j189eIKfme4UboMo9KJmyWdV5zX++BP+MwOqDQCsqROY7TSM2JZ/hrcol1KbGe6iN3"
    b"KspB+1FqGEroV3o/SjOKL1Hpo5G/xhdkBjoJ6swePgAAAABJRU5ErkJggg=="
)

icons8_system_task_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"TElEQVQ4ja3UzStEURjH8c9goWyxY1jITkrs8AewoPgLSLKztLJR/gEpxcbWwsbWhrLwlh3K"
    b"S40lKYlmIxbnjJm57ryU+dXt3OeeX9/znOc852bQiS6N0VMG1zhqEHCsCR9YRf4foHxkfLTE"
    b"DxN4x26KeQD3ceFKmo4MBWAzcrhIMW9iXfWyDEWGpiomyKIPwzV8v6oFnI3ZNQw4hR101OFF"
    b"sYbQja2SuBlveMWtsPUnrKEtwXkWzqAM+IL9hDEXxzOMYBkPOEz4RtMy/JR+ynCKDdxhMWV+"
    b"qPBSV11wiW8s1DIWMvxCb+lKKZpDT3yS6sYjZHCOSaygtb6E/ygvtNeBCPyPloRDg/OWas46"
    b"dSLUF2HL2xisYG6P40uFOKmrTIWJcfQr9tdxHEvjGyk/jDRgFntC5tU0jxnF5kd5YxfULrRQ"
    b"rZ7LCne8DPgDBhc9y356EnYAAAAASUVORK5CYII="
)

icons8_laser_beam_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"VklEQVQ4jd3TO0udQRSF4UeDCoJi4KhJEy8g2EQLQRtLCzsxfboo2NmIlaXgHxCTJm2wE0UQ"
    b"QSy0ECxELCLGpEolaiEkKHgrvi0eD4PfUaxcsGBm9ux3LnuG8rQZzlVlmcCy9XqBHWh/KWA9"
    b"NjDzVOAbFBLjU2jGbN7KX/CpqD+Cf6hz/2zqcIH5PBis4Qbr6MaHABaKgAX8Rwua5FxZFcZx"
    b"ikt8jWOVAmcjdomxcnZawFwknCeA5xH7hobS5AoMoTMB7sJH9OBnjHViB3vYTeTsw6Hs7lJe"
    b"lFX0KtyEpUfm/4JqvC1xG77jGO8wGH6Pk4i1JvKqE7vWhyNcYxt/ZMUaj/Z2xI4wKnuvj6of"
    b"C+jFKs5wED7DSiy6FcfciZxcDUXCpPsqT8bYoKygn/EXv/NgNbJiHUb7DliDHxgomluLxjzg"
    b"ROxkOPrL4Wdr2sP/2iDxiFO6BclXXCxkXMUWAAAAAElFTkSuQmCC"
)

icons8_direction_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"yUlEQVQ4jc3UQUqCURDA8V/5RVAtwqBw0TmkGyhoeA33LTtHuGihtIs2FXoCpWu4EFwpHcGF"
    b"84ELKV7fo/pv5r1h5s/AYx7/iBM0cws/0MkpPccUt2XiIOIlVlFQw3WCtI5H9DEpItnCGDc4"
    b"insKxzHlJLFvL3d4RvFd4a/LrvCQS/Z3FBig8VPB4c65hiEWWFYaK2RPuK8qKjdlgB5eE/vf"
    b"wzFDF6Pyyd/QxgvWCcJ5xE97tqRl+3tcJE75JZ2QnuWUNnGaU1iJDUKqGvOJPKhrAAAAAElF"
    b"TkSuQmCC"
)

icons8_scatter_plot_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAGYktHRAD/AP8A/6C9p5MAAADtSURB"
    b"VDhPzZS9EsFAFIUXjU5FT6FEpVFTKAyFFzKeAk+g1niJtLwFJYbhnLtZk2wiNkuRb+ab7Nlk"
    b"bvYnG1V4SuHV0IVt3XTmBvfwIilCBz7gM6dX2IcJ5pAP/EQ5vP6NrIIreIYzSY5kFeQS1OBY"
    b"kgf2Gk4gR9mU5DHib5tygry/luSAXbABR7AiKT5i9g0hn/mIXfAAmZeS4iwg7x0lRcjaFFM8"
    b"+hJDWl8Ce4R1yGmZKU8h168FvaZsYzZlI0nDs0/f5DkpW8jPZidJFwpCe+yw4fd1100nWJA/"
    b"ExobpaEKB7rpDP9QqcWKilIvu2w5UIty+GoAAAAASUVORK5CYII="
)

icons8_bold_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"t0lEQVRoge3ZS2icVRQH8J/axCrUPrQ+qlB1UaGCSuqLilAUEbTUggtBpRVR0o0ggqBkZTfi"
    b"RisKVUGh4ANd+IAspCqoGBdVWkUqVtCurFip9RFN0gTHxbnjTGK+b+4kXzKDzB8+zsA9c+45"
    b"37nndT966KGHMpyUwXMedmFVRXv+htFED6VnH/6oSH4h7kNtgZ8JvIftOGUuSuZ4ZAd2YxhP"
    b"z2WTGViO03AWLsF6XIv+tP41BvFJBXtNww7x1nZXLbgJy7EN36a9xnB71ZsshiF19OHJtN8k"
    b"rsj948kLpdEcMYmH8AyW4MVEWyKLKQNLsaYFzyiOZsp7FFswgFvxztxVayDnaI3Iy04n8B2e"
    b"E4Fehp3pP3vmofs05BhyPPEcForO9hw13agx3FEi8+rE99X81G+gHUNWtJDVh43iLdeNKfLM"
    b"2YnnpxwlFzvYJ/GpKHx7RGwNFvAew984U4aencxa9bN/ZcF6TaNg11oJ66QhxxJdXrC+Rhjy"
    b"sy43ZG2iPxasX5folznCOmVIvyh88EEBz/2JDucIrKog1rFCcSPaJ7wwIIxYJ7zxwiy823Gj"
    b"OH4v52xctSGH2+S9TcwlzdgmjKvhQfyaI6wqQ97EVuVjwRR+EYPUsHjTY03ra/EsNgsjHpHp"
    b"jVwsRve7UhhZE7WjrOLPim7pfsfELEJ49THc3I6AbjFkXEyJG/CqSATvilOQNfpWFSMX4qoM"
    b"vnER3Ac1CmIz9uMuvITXxbGewgNVKJkTI/URtZ1nH+5UnCAG8GfivaGVklV5ZHWib4vGsAhL"
    b"RRN4mfDgK2KAulu8+WbsxxCewhPyPF6KKtv4Ok7FvRqZaqiArw9HEs/lZQI7FewTIg62CiUf"
    b"FkrPxCTeSL83lwnsdNb6GF+IDrjo6IwkWtTuo/OGEBdyNLrhmfg+0QvKhHSDIfUg7y9Y/z3R"
    b"0vjrBkPWJVo0l6xMdKJMSKcN2YhrRL0YKeCp35eVXkJ0ypBl4pZ/OOmwSxgzG9YnerBMYNXz"
    b"yFv+W9iasQzn4xyNdPuaaBKLUL/Mfn++yuUUxEPaa0+m8GFSsmyG2ZL4jyhOBqjOI9eLtqMV"
    b"RvGDOO8nWvCuxvPp984M/pZYzM8KdZyLz9O+e2V8kOp01poNN4nbyA1irr9Hl99rNWMJbhFZ"
    b"bC8uEq3LJhEfWQJycQYubk+/WXG6qNKrcKmYOzaJb4pEJX9cpOTxCvb7F4MW/qtuTdSJIZGa"
    b"20aORz7CAcV3tO3iLzG/HBffTQ7gM3xTkfweeujh/4x/ALbGH+I/qO5zAAAAAElFTkSuQmCC"
)

icons8_italic_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"LElEQVRoge2ZTSuFQRTHf14LKZHIRpSFknKFFSI7G0ufga/mI9goG9d12SgLShaKiPKW12tx"
    b"ZrrjGlceZ+bpqedXT3Pvv+495zTnzJmZB3JycurREMnOOrDi0c+ANeA5kh//ohV4Aio/PKPp"
    b"ufY3JhGHT4El86wa7QFo1jCi8ie/MGPGbWDTfF42Yxl40zDSqPEnvzBlxl2PVtQyEiOQaTP6"
    b"AtklI3QC78AL0OboF0iNDKfhVBIWEIf3HG3YaNcoLv+hU8umVdGj7SABqRA6kCiFDvFmJNOF"
    b"3o+kzj3VftVkvleAPk1jIWfEzkaJatMbAzqQLn+haSxkIL5a8BW/CjECyXR9NABXSC0MOvqB"
    b"0ebTcCoJI4jDl47WDrwinb5T22Co1LIptONoBWT1OgTutA2GDsStBV9PUSNUIL7VKXOF3gI8"
    b"Ah9Aj6OfIHVTSMOpJEwgDh87WjcS2BMSqDohUsuXVjPIkryPrFzqhAikXqGrd3RLrBnJXKHb"
    b"pveKbA4t9mg7koZTSZhDHC472pDRbgh4s6mdWvUOUkUUj7a1aAcS7WhbS6hAfGeQzBR6L9/v"
    b"c5uQDWIFGEjJrz+zjDi85WjjRjsLbVwztVKrD4gXSGbqA6pNb8jRykZbTMWjBNj7XPdo24Zc"
    b"Xn8AXaEd0EotXy0UkC37EXCrZOdHtAOJuuN10Xr1ZgM5p/rOY9aMJSUbUbBNz/dM1/mdGloz"
    b"soHsfGsp8fUlT05OTs7/+ATr8IVDpqnfoQAAAABJRU5ErkJggg=="
)

icons8_underline_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"dElEQVRoge2aQWtTQRDHfxWqBatIRWirRSu29KJIVTz10LNKToJ+BUX6CRS8KPgBBMWTB1u8"
    b"txdFQakerEhPCmqFinq1NoKxvsTDzLrlJZV5ySZdZX+wTHbe25n9Lzv7Ql4gkUgk/kceAbVc"
    b"e9qGPPPN5ukyJqi1ON5K03m2FEzUZQkagMJ5igqJliQkNpKQ2EhCYiMJiY0kJDaSkNhIQmIj"
    b"CYmNJCQ2rEJ+qu1VW871Q7BT7bdcv2IZbBXigg+q/ax2wDjeQr/aL7nYK5bBViFLueCuP24c"
    b"b+GY2vdq3aItNbi3DquQRbUTamfVlozjLbhYLrbLtdjg3qY5h/x49kL7Q8Av4AewP0D8YY21"
    b"BuxT30vNeTZA/D/sAL4DVeCQ+u5oonsB4t/XWLe0P6q5yoQ9UAA/8Wnt7wVW1XephbhTGmMF"
    b"X4NO2O0W4m7ICHIMV4Hj6isBGbIlmhEzhWzRDDijvpOaowIcbGG+f+UGslJvgb51k8nUPwMc"
    b"MMQZxq96hl+E3cA79V8PNelG9ADPNdEDoFv9JeRZU0OKdho5IMaA7drGgPOI2Ap+O53WGN34"
    b"1xfzwLZ2CgF5cC1rwifAHvUPIsW6Rv07jnzLgLv4mugDHuq1T0j9dYQjwEf8Njux7toQcBGY"
    b"A14jB8Kqfp4FLuCPWJCacNtpGTjc5rnXMYDfZlVky4wUGD+K1ElVYzzDf03pOD3AVeS8d4IW"
    b"gMvAJPU1MglcQR52TkAFuEYHasJCP3ATL8jSykhNBTliQ79G6wVOISt/FDlmd+m1r8AH4BXw"
    b"GKmhcoMYicS/yFbgDfZCDtXMf0oo8uPDRi/z28lm5NxcfgObzr2fydjmggAAAABJRU5ErkJg"
    b"gg=="
)


icons8_camera_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"fUlEQVRoge2YTU8UQRCGn5j1ICwfiXjBRC8iGg+i6NGIGlFCAsKP8AcYlagJQUGvft80XrkY"
    b"DZ5wMTEQDiaCXhSvApGDUeQ7UWA8VDUzkN3Z3pleVsy+Sadnpqverpqu7q5uKKKIIgqBHcAN"
    b"4AuwDHiWZVl1ritHQVECvMXe+ExlGCjbXNPX47EaMgU0A4kcdBOqM6Ucj+IaM0z43xrKoLcH"
    b"+A38AQ7H6L9OOX4rZ2TYDH06dGpbb5zOFb3K1RlFuQS4SLixNk42Rul8AxrT8M4Do8AtYFcm"
    b"xQZgPKD0LoPcUIgDHjAIbIvthnAMhvQzA7RvVDqHxKMHPAdOkNsk3SyUIj/8JWLrCtBmGquA"
    b"79pwqQDGRUUHYvMvxAe69MObPHZaqx0PAGNIrM/rcwq4CuyPwNuH2H4T4KO+nAwINAOTwATQ"
    b"FM12AOoR4203wQHVscUp1RsFWNCX0oDARIB8PIIDCeAhsKocP4AnQAsyOqVaaoFW4KnKeKrz"
    b"ALs5WqY6swQMDiKOI5VImHrIT+oGyi30yoEeYBF/dCot9NbsT+dIE+LMOHDegsxgO74T48CR"
    b"HHQN6vF/ZIrsIxPqSFQ8xHeiOgZPNb4z97LIOnekHonvBaKNxEYcRcJsJQufc0fM6tTtgMvg"
    b"tnK+DpFx6kgt/upkM7FtUQH8VO6aDDIe4LnIicBPE16gS6EjzCDpCMCFMEFXjpzR+pUjviAM"
    b"59kwIVeO7NX6kyO+ID5rnfWA5WKOzClHMiZPOiSVey5Du9M54mofSgdj46qNUFxMaR1nE8wE"
    b"w/ktTMiVIyYfO+iILwjDGZrzuXIkpXWLI74gWrUO2xSB/2RDXPcQEyZF6XHAZXBHOftDZPKW"
    b"NC4iCV9cHAOWkKSxLkQuL2n8A+WaAHbH4NmNn8bfzSKbF0cS+CE2CRyPwFEHfKXAByuQ42lK"
    b"OReRVLzCQq8CmRNL+Kl77KNuXCSA+0h8e8jK8wzJYA8gaUdSn9u0zaxOK0g42V4Qrtk/S/7y"
    b"pENI9mp7HZQit4WiHP/6lA/60uDE9PSoAa4g4TKGJIBzSGbbD1wG9kXgPY3YPgJys+3hH2C2"
    b"Esxod4Fcz8/oh47C2ZQzriE2TwM7zcd2/InZh1xF5mPOxEUSCSczEiv4udga2pCbbduJWegy"
    b"nc4JgyrkZnsE/9T3L5VZ4D0yJ9bCqYgiiihi6+EvESa3u9XaFVMAAAAASUVORK5CYII="
)

icons8_detective_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"tUlEQVRoge2Zb2jVVRjHP1eh0nStsk1tumYJScIKCcI/s15EqETEZjgXZNGLwJIKp6KZoIXa"
    b"i15J0KuyKGTYH2dK0YvKUhFLgsiMqBSZkhNXs7np7nZ78TzH89u553d3f/f3u/dq7guH391z"
    b"zvOc5znnPH/OGYxgBEVBKib/RGAhMB+YCdQCFdr3D3AC+Bn4GtgL/BVzvsTRAOwG+oFMnq0f"
    b"aAfmlUHfLNyJrKxRrg/4HFgJzEF2ZKy2WqW16pi+AN9nwLQS634ZLcB5VeQc8DpytPLFJOXp"
    b"UhndQHPCOg6L1djV3ANMjiGrGvg4IG9LbO3yxKs64QDwfIJyX1CZGeCVBOV60YJ11JYiyTcB"
    b"Y0kR5APi2MYnXi7WJCrb+ExdoUJy5ZG9wALgE6BRJ3MxAXgImAXcDdQA47WvG+gAjgFHgK+A"
    b"zhAdPgIeR6LZo1GNyIUGVbyHbMeuAJ4D9mPPuGlG+Q79HewbAA4Ay4GbHJmTda4MMDdJQ3ar"
    b"0M0BWiXi+OcCih0GXkMy+60eObcgi7IJOASklbcL2OjwbNa+XUkZMRFxwAH9fQOwAfgbu7oX"
    b"gPoCZN/P0MTYjSzEGJ0rDVwCqmJZoHhGJ/kGycy/6N+nkB3IAKtCeBuAddrCShETzo8gPpMB"
    b"fgMeRGqyDLAsrhEA21XYn8iu9CKrNg44ihytGx2e8QwtXYKlyDhnbAWyuz8hx/VNZBcGgZPK"
    b"904ShvwQUORHpKoFiUoZ4AMPz4ceI0x73zO+Tfum69/1SJVseA4nYAdnsdn2+gB9kdJXOOPv"
    b"QFYzzJBBYKrD85L2LQzQxgDblH4mqtKjPDSTB94ALgbot+vXvVPUkzsfpYB7Hdpp/dYEaL3A"
    b"i/q7gojwGRKGPv2Odeg9efD+6/xtZPQ59NH67Y+gF+A35Lx+3aRlVtE9JgcQ5w1DF3DQodXq"
    b"t8OhV+o3kZvk98g5fcCh34xEl/0enmcJ95GnPeMPIsfWXazZyvNdgboPgQm/vkLxSyQkz/D0"
    b"NSN3dGPAcfwV7T0q4wtP30rlfTuq0j6YhLjP0/eI9rWH8KaQK+w0wgPAHpXxsKfvW+1rjKBv"
    b"KKoRZ0vjLxVM4mstQPYqbKJ0UaVz9mN9JTbaCb+GTgD+QPLDOvJ7UkoB65Xnd/wF5lads60A"
    b"fUMxD1sc1nj6pwO/MrQmC8Nc7JE5BtzlGTMFySODZOec2DClfBv+Va9Eyg9zJzmOBIpNSG22"
    b"XWmm5H8P/5FJATt13KcJ6n8ZddjL0Zoc4+5DosxpskPvKe3LtcprdWwn8V5ncqIZu6KLhxk7"
    b"Cnm7mqVtEsNXDk9gd/SxWJrmgfVYY9YQ/70YlbEWa8QAxXmlyYIxxviMLwDkiylYnwi2NLA0"
    b"npr5YQnWZy4goTnKlbQKCbG92GuuucMHjSnJM2odNpqZifchpcVsJJlep61aaa1I+A0qvQNx"
    b"7KXlNAYkN+wi2r8VLiK3S7cYDTOmaC+PPlQBTwHvItfTTkThHqSAPAS8pUrdlkNOM1eAMUlh"
    b"Mdk7nAaeLKdShSLMmJKE5qTxvzKmiWvAmJIkzaTRhLwTXDvGRHnXKhd2Ir6RDtBG47+gXRVo"
    b"xO7MhjLrEhtNSCU+ghGUCv8BPlKp3kSlWv0AAAAASUVORK5CYII="
)

icons8_picture_in_picture_alternative_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"qUlEQVRoge3YUQqDMBCE4bF4/0tpz2WfIgmY4sNunMj/QZ+EsrMxsKsEAHjYV9Ix2W8rxS9V"
    b"kCOmH8MtkrT2HkygafznqSqiEcQNQdwQxA1B3BDEDUFuil4NNnVcjfGR02/GalDqa+q9GuMz"
    b"RDTnb1O4I24I4oYgbgjihiBuCOJm1NCY/oE8+0T24P/r7iO1srzMoqn31XdkplM51ScS/T6P"
    b"cOvOAADS/AAtmFEkt1mw4AAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icon_corner1 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAIJ3pUWHRSYXcgcHJvZmlsZSB0"
    b"eXBlIGV4aWYAAHja7VlXdiM3EPzvU/gISI1wHKR+zzfw8V0NDMNQFC2R+2lypaFATKeqDpil"
    b"+c/fQn/h5Yt1FDjlWGI0eIUSiqv4kM1+7as1Yf1eL++O7+x5na5fOCx53bn/jPPYX7HOtxtS"
    b"ONbbeZ1SP+TkQ9DxxUWgV82q7NiXw9WytW6Pv6kc99Vw587x08axxvvy+HdICMZgyPOO3PTW"
    b"G/zOqsXrj/VV1/Db+YJNula9vnTdPY8dXT8+BO/66SF2ph7r/hwKMvHYEB9idKxbfh67FaF7"
    b"i+xN8+kLBHma+9dd7ERGFpnbuxoiIhXpcOriyvqEjQ2h9Ou2iHfCD+NzWu+Cd4aLHYgNoNnw"
    b"7mTBSkRWbLDDVit2rmu3HSYGN13C1bkODHQt++SK6wDA+qBvKy754gf5DEw6UPNYdldb7NJb"
    b"lr5uMzQPi53OQhiQ+/qmZ4vvvK+CRJS61pp8jRXscsoamKHI6W/sAiBWjpjyiu960x1vzB2w"
    b"HgjyCnOGg9W0LaKxvXHLL5w99rEJZHZq2DQOAQgRdDOMsR4ImGg922hNci5Zizhm4FNhufPB"
    b"NSBgmd2wJMDG+whwslPduCfZtdex28soLQCCffQJ0BRfAVYIDP6kkMGhyp4DMXPkxJkL1+hj"
    b"iBxjTFFrVE0+hcQpppRyKqlmn0PmHHPKOZdciyseJYxLLIlKLqXUCqUVoivurthRa3PNt9C4"
    b"xZZabqXVDvr00LnHnnrupdfhhh9I/xFHopFHGXXaCSrNMHnGmWaeZVYB18RLEJYoSbIUqVfU"
    b"DlTPqNkH5F6jZg/UFLGw9qUbalhO6SLCajlhxQyIuWCBeFIEQGinmJlsQ3CKnGJmikNSsANq"
    b"lhWcYRUxIBimdSz2it0NuZe4EYdf4ea+Q44Uuj+BHCl0B3JfcXuC2qiro/gFkGahxtR4QWHD"
    b"puoy/qEev3+lTwX8L+j51fco03XpXEZq3aTpKjUeTkJrYfgYs+PmQssxtprHKNnblLgbcAPd"
    b"OqPRtBFbDiJg5BSbkwwDznpR+JtYn0TsqF70aykup5q0C4Kigvo8bHMjZdxkUjNJug9gevcy"
    b"s21oYTIkU2m6Nc9h9Yp7xkSXk4oBCfoEVkc0Vd94gpv8nSS0bAhTWYekixydFbYkY7YsY15L"
    b"o23Y53bRNuxzu+g+YJ/YRfcB+8Qu+grke3bRVyDfs4u+I9jVLlRZMaUhJWaDzC5o0QNltWot"
    b"LTr0WNb5qLvGtcdZO2df3TRzomdAapljFhbvWG2fHarFsRH8k2Y4lGUlmj1KptREU9Ow6sD+"
    b"s6sgAXcmGXPJJYQj00qnazIt5QiLfqnqkZ74pAZgP9Sz9t9DbKtBDE4ycMmJpRkbhhG4zF0i"
    b"Rj2EoDXu6HnDN1cLm14bQsecZ0J7aKlq7iLl+QDeZzkI6XgHWI3dIR68oUdgDuhLXNDLXNBz"
    b"MHbBdZNFG6wtS6GXBf2WdJGj0G9JsGXJUujP0uhi2qeW0Z2bH1lG8hC0dy2jx6C9axndOxoK"
    b"/gI3YuVp/IjRojGAw3O4WCa3xC1zbJhOIpvKpeBkkkCRPtkQBoRQMTdos5FoZJQOJaHauW2K"
    b"phZQNsTOmqA8u5UGy6WXgDEE5nfLDqjNPHJFq5rlt6OEn6q3+rb00lzJB1tqXukA1e2mGlVh"
    b"q15tSZXDTOgusfV08oLeceOZF/SOG8+8oHfceOYFvePGsyu948YzL+gdN555Qa/d8NiOSUbC"
    b"FDNjFj/rqKh7aZTZoxltRoxEtkikCUeqzzhNlBmy7abOHWybIrKvr8yyO69cWF9icsJpvKmx"
    b"xcyGXIxTlmsVR5WBARzneIupWmOCczd6UkKAwk5T3ARD9BM6Fny46tlaHIXDAqhZorTZjXWD"
    b"mNYSzl86lXW/uwYnPR8jM2EXjyZGtFZEuya2XlzTJxQ+sTgcZg+zcOPNrPUsQORi1oNR6jw9"
    b"en8yS4vZ2azDKChZZsGTwzA6LDvM0tJ5M2wWBLViePXVp9xax8EJxKkYBxLm0xHBn+FsTOIK"
    b"Clv3ubjgQgRkfiB0M+Fgg0KnT73u+vVumWwuLbOslulWywT8L2mn4Qrow4fQV1e6LVjxl359"
    b"dGsgd3TrNS7wofxpAtE5g37jzNkXeuWMgnWmsD6fXDZcOcxKlR4HbaIFX9eGobtnCWFDp48Z"
    b"ebHhP690S2Gl5tdSpNWgDZ2JNn/WTKRnEJwvwhqI7GIdefmpzuOa+mM5XVVo16NLIdqq/+tg"
    b"Y595Qe+4cfVC0xCBXi3720AfNeCx7jyUnSsJCRPFj5j7C2Z/xnB63iN+z3D6Sbr+hOF0ofgP"
    b"GZ6w8SnB6BdZ8JKh9Lrj3xh6PjCczwvKUXrZ888MfeDnYvuVoXSjqBZ0HT6PQI0d1AeGfhty"
    b"+kLRNxlKP9h4x9Dvz0z0pAhvRq3clhNDMR5gTLF1XsbnONiHlh3GZ1rzc8Q/xvnrmJ+5OR+b"
    b"W/MzQOU1PteVAU8er+ynK3R5vDItjOpxMTyYMbRBSw/LnZ722KSyQhYbwGDc7FbT9CUltExC"
    b"osTCkDVG7ANjUGBnEg56gzEAlYLzcYUKTqWNMw/PHKdPOG0fBX0tw084PnG6yc3r0Z0RpJly"
    b"rSNxGG5OCYNyNLlihBi4YVZwL7pux9BwVw+K2r7DbTWMKBcrjMG6sccvZMTQpEenNX7F8UAE"
    b"qbARCe2CiKznXbXeS9L/GHAbEAVj7EEr1pM0zDyP8lY6+F3DzxKvttHNuM9so5txn9lGzwL3"
    b"zvGN/shj0f8F/WFB2jYKiPcvpWoLVpagByQAAAAGYktHRAD/AP8A/6C9p5MAAAAJcEhZcwAA"
    b"DsQAAA7EAZUrDhsAAAAHdElNRQflCh0GIQzjOpIIAAAAc0lEQVRo3u3ZQQrAIAwEQFP6/y9v"
    b"v1AqxiKTs5eBXQ1YScYJc41DBgQEBAQEZGbutwerassKkKRECwSksewzRey4UEQLBGRh2f+0"
    b"AYgWCEhz2Ts2ANECAQEBAQFZ8bLvWtlFCwTkQ1/9s4OAgICAgBwEeQBF4hNpcTofVwAAAABJ"
    b"RU5ErkJggg=="
)

# ----------------------------------------------------------------------
icon_corner2 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAIFHpUWHRSYXcgcHJvZmlsZSB0"
    b"eXBlIGV4aWYAAHja7VlZluq6Dv3XKO4Q3MnNcNxprTeDN/y7ZQcIFFSdgvN5SUHAcWRZe6tL"
    b"0fz//4T+wcsXkylwyrHEaPAKJRRX8SWb/dpna8L6XC/vjmv2fpyuFxyGvM7cP+M85leM8+2G"
    b"FI7xdj9OqR9y8iHouHAR6HVlXeyYl8NVszVuj99UjvtqOG3neLdxjPE+Pf4OCcYYDHnekZve"
    b"eoPPrKt4fVtfdQyfzhdM0rHqvY/4ZJ+e246uXx+Md/32YDtTj3F/bwoy8ZgQH2x0jFt+brtl"
    b"obNG9rby3QU3zDTn18l2IiOLzL27GiIsFenY1GUr6xsmNpjSr9sijoQ343taR8GRscUOxAbQ"
    b"bDg62WIdLCs22GGrFTvXudsOFYObLuHsXAcGOpZ9csV1AGB90MOKS774QT4Dkw7UPIbdVRe7"
    b"1i1rvW4zVh4WM52FMIs7vhz0bPCd4ypIRKlrrclXW0Evp5yGGoqcfmIWALFy2JSXfddBJ96Y"
    b"E7AeCPIyc8YGq2lbRGN745ZfOHvMYxPIbNewaRwCYCKszVDGeiBgovVsozXJuWQt7JiBT4Xm"
    b"zgfXgIBldsOSABuwH+Bkp2vjnmTXXMduDyO0AAiGiyRAU3wFWCEw+JNCBocqew7EzJETZy5c"
    b"o48hcowxRY1RNfkUEqeYUsqppJp9DplzzCnnXHItrniEMC6xJCq5lFIrFq0QXXF3xYxam2u+"
    b"hcYtttRyK6120KeHzj321HMvvQ43/ID7jzgSjTzKqNNOUGmGyTPONPMsswq4Jl6CsERJkqVI"
    b"vaJ2oHqPmn1A7nvU7IGaIhbWvHRDDcMpXURYDSesmAExFywQT4oACO0UM5NtCE6RU8xMcXAK"
    b"dkDNsoIzrCIGBMO0jsVesbsh9y1uxOFXuLlXyJFC9zeQI4XuQO4rbk9QG3VlFL8AUi9Umxov"
    b"CGyYVF3GH+Lx+2f6VMB/gp6ffY8yXZfOZaTWTZquUuPhJLQWho8xO24utBxjq3mMkr1NibsB"
    b"N5DFMxJNG7HlIAJGTrE5yTDgrBeFv4n1ScSO6kUvS3E51aRZEBQVxOdhmxsp4yaTmknSfQDT"
    b"u5eZbUMKkyGZStOpeQ6rZ9wzJrKcVBRIWE+gdURS9Y0nuMmvJCFlQ5jKOiRd5GitsCUZs2UZ"
    b"87002op9rhdtxT7Xi84G+0QvOhvsE73oK5Dv6UVfgXxPL3pFsKteiLJiSoNLzAaZXZCiB8Jq"
    b"1VhatOixrPVRd41rj7N2zr66aeZEzoDUMscsLN6x6j47lhbHRvAnzXAoS0ske4RMqYmmumHV"
    b"gv3PzgIH3J5kzMWXYI5My52uzrQWh1n0oi4P98Q3VQDzsTxr/j3EthrEoJPBlpxYmrGhGMGW"
    b"uUtEqQcTtMYdOW/45mph02uD6ZjzTEgPLVX1Xbg8H8D7LAchHW8Dq7LbxIM39DDMAX2JC3qZ"
    b"C3oOxi64brJog7VlKfSyoN+SLnIU+i0JuixZCv29NLqo9qlmdNrmR5qRPBjtXc3o0Wjvakbn"
    b"jYaCX+BGrDyNHzFaJAZweA4Xy+SWuGWODdVJZFO5FHQmCRTpkw2hQAgVdYMmG4lGRulYJFQ7"
    b"t07R1ALKhthZHZRnt9KgufQSUIZA/W7ZAbWZR65IVbP8tpTwU9etvq11aS7ngy41L3fA0u22"
    b"NKLCXnqlJV0camLtEltPd7ugd7bxbBf0zjae7YLe2cazXdA723h2pne28WwX9HIbASx3ZbqC"
    b"qIeOdnrXekPoQ4E6O+YpR8XUJiWIi0y9F1tQpKJTQNRN4qr4tBVbfiaZRxMj6jhxWaUX17Rb"
    b"1xJc0A0jU6QicNrtPRNFd1/eg0QixewAXdd2pk0RntiXl9ntYw7+4NULV9JqjRIaIy2Xut/h"
    b"nJM2rnG2GcxVMY0A94odamkY2YrRoZmsJh0KH4o9qIXPm1pbqUMlDTKqlD6JaO2s1qEUbPGg"
    b"1vf2Ih4oB0tFMhzT+WGnGdxCweUWOHdpwKqk6F2cA0kUGaijqe9ojYtFyMmcxrIZ+jXlSzEz"
    b"syCkrHUqemzN5xXNdsAfWkb/U74jTXjyyMBN/WVMuTAQDeJ3yZtW9r5Ku3Okw40WmzWMQo+x"
    b"NbxoejrT0wt/sJXHndC3W3m5/sMZBl++9tLg6BIBDS+grVNqBF8tiNLUBCWgnUXiyCqPVrnV"
    b"f45HbTwvZy7VDF16A/t9RLrJUrYuSdqIQE7YTQY1qyoNzWtWtbNvnunVhdRvQ8tMy0i6rUcz"
    b"sTiYmzbBP+c3PWfF7/lNp+r0I36T/Q3x7As/wFc6kRPLnk2Fjamx7pn50uR0peZzZh68BEG/"
    b"MvOuZaWHnvXES41/PzHzYDm4SQc5IeszZtKPE78w87kD05Wa3xr7BS8PVoJnKI9XrFpMesHL"
    b"Z5n/npfKc9rU3EQvK/q9YuZdIfaFmcR/gZFXQYuaV2bWkDI3LZRz8VqH2N7CQKRzONfi9GEa"
    b"9pS0UjGtjI79JQdjZ5M4+gGGjLlSNDb19SHK/TOUaWHFvrNtMGMYeP+UHlZg6GkXR5A1oUpU"
    b"pUbAUKm9+1pjLYZr8L4zkjma1xZr7mhtg/7zhcKcMfqCvDzBBu5jHJT5JcPpIfy+zXD6Y1fY"
    b"DH/ZSdEn7edZFn3Sfp6l0d9ojFUWfdQYn5IqPavzl2YK62ZkaMrIpa/fdW+tE2QBP7uLxwNE"
    b"crXVof+PaO36ADGhV+TGxe4HiHBSOEJeDxD9kKFF5SgPzzrojx+K/HD+T9DfEIRYPQq8+1+q"
    b"fwBcjQsW6gAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1F"
    b"B+UKHQYkOcj+om4AAAB3SURBVGje7dlBCsAwCATAWPr/L9svlJoakPGcy8BuiCQyc02Yaw0Z"
    b"EBAQEBCQytxvD0bEkSdAZoZogYA0lr1SxI4LRbRAQH4se6Wcuy8K0QIB2VT2Sjk7VgDRAgEB"
    b"AQEBqT7jT60AogUC8qFz/tlBQEBAQEAGQR5Dnxdpa7PYOgAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icon_corner3 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAH/3pUWHRSYXcgcHJvZmlsZSB0"
    b"eXBlIGV4aWYAAHja7VlZtiOpDvzXKnoJySAEy2E85+3gLb9DgOfh3rLrs+26ThuTQlKEJhf1"
    b"//9v0D94uHR48iwxpBAOPHzyyWa8icd6rKs5/HydD2f3d+Z2nc5fWCw53bk+hr73Z6zz5Qbx"
    b"e73crpPULSduQfuLk0CnJ+the1/0Z83mutmfKe37sr8yZ/+Vttd4Xe4/e4EzGkOes2S7M+7A"
    b"a9RTnP4Zl3UNr9YlbNK17JwLeGXnn/uOzm/vnHd+d+e7I+91d+sKOsLeEO58tNcNP/fd9NC1"
    b"RuZy8s0XoEE/rh9XvhujxTH6si77AE8F2kadTJnvsLHAlW7eFvAU/DHey3wmPCNMrECsAc2C"
    b"ZyWTjIVnh/GmmWyG6fNaTYWK3nYruFpbgYGuRSc22QoAjPP6NMOKS66Ri8CkAjWHZXvWxcxz"
    b"0zyvmoiTm8FOayDM4I6HJz1b/OR5FjSGUteYI559Bb2schpqKHL6il0AxIztU57+nU+64s1x"
    b"BawDgjzdHGFgPsoSUdhcuOUmzg77GNF/rNAw0rYAuAhnM5QxDggcwTg2wRxirRgDP0bgk6G5"
    b"dd4WIGCYbTM0gA3YD3Ci1bNxj5i517Jdy0gtAIIRIgJokssAy3sGf8RHcCizY0/MHFg4cuIc"
    b"XPCBQwgSNEdlceKFJYhIlCQ5uugjxxAlxphiTjY5pDBOIQmlmFLKGYdmiM64O2NHzsUWV3zh"
    b"EoqUWFLJFfSpvnINVWqsqeZmm2sI/xaaUIsttdxNB5W679xDlx576nmAa8MNP3iEISOONPIZ"
    b"tY3qLWrmDrn3qJmNmiLm5z65oIZlkZMIo+mEFTMgZr0B4qIIgNBWMTui8d4qcorZkSyCgi1Q"
    b"M6zgNKOIAUHfjeVhzthdkHuLG7H/I9zsK+RIofsbyJFCt5F7xO0Jai3PiuImQBqF6tPDDSQ2"
    b"bMo24h/y8edX+lbAf4K+FOR6QElCLQqxDxNltAPEdGOUYZzoN6ZlN7rJrtSA/IuyRG3e0hGS"
    b"DXEpoVSQCFwZKutBEsJ2ybqThEoLYSprSwLX7mT9Vi9ain2vFy3FvtSr90EdHyunJrgxdZsL"
    b"wnCwL765YKK1xSJeORSOrXEsaP24mlZ7dZDqWmm29ODzIJzXUpXRfTYdtR8K5DTV96GyR1r1"
    b"oxnP2uLxmyv9tOHJVQvt9ZJkL5G49CNLTK5y66bCJEHrMcTn2FvoRXr1qXM6XIQvakRzoomR"
    b"2bUOxlW8ZnUjARMx24vwzMZkTEzyxASGb654YxckCscCJWSVBlgodygTVK3mSz0k1+oyd/ip"
    b"ZTi8FtUKXwaoU7Pxxdl+9A6NkB5Nbz1xBeJo/bhXM4pDL1eTR9aEEtWwhftji1lJUFp0Q/Ue"
    b"yUZkYSgfbfaqUUMlQa8szdFQp7E23t9d6X4Bk8B5iZGuRzVWz06oVNlAmaJcSR6FY9iDpU1S"
    b"okAWMCgdPeKWMKZLM1oalZgvcLtDejPTvfgKzJqQHOwhJbvAKO80JniImbI4meYmsDLqdYCV"
    b"hTtqCSgj4HWv+DBUGv4NlZXm4Y6C1W5hSfuG4Z8w+ynDaXnLX7kKhqmzpqtQTn9wOeT1uDSa"
    b"UCmXvMjiEixSLk3Xg00pXNiEXLLYJGOyyW02WWoSERzHFS9B/B+ZqbrdcLPRmZpfMpNebnhg"
    b"JjRVR71g5g/OfsHLzUrwbLMSIbKJ+YSXM10rLxeXnvBy8ZxnTqdNTsh7xczJc+XmW2bSe8a9"
    b"M+bWFvqNMb8hOk2r/wK7KV7g/ordpPT+G+wmpffH7L6ygj4N0pMVEMk9GbTHjBkbRJRY0Jyw"
    b"pGAy6iG4ifqIM1oP7IcDgNVFzB04io/oMHOPLurlADOAFk3Qj+wLJi0tkmVm5uSKuqFiDEFb"
    b"wxhODvTuAHQVx9SK/hThFC8NNKBKPFlTMbUMTBuTQSjYIEJvVattndXWJ8HsMGlopMzgkKBR"
    b"Evt0VTTkF4vG/AnpWq2tlPZKduJ4p9hWC6ZOxWhrNkk4LordqAWf3iq21NpK4Yiu+ehM3Jf5"
    b"BqH1znT0XN4jQ2LSG0cPcRxBJ7pWEPy9BvSCnSuXlkboPVj0cxgLE4LI1YSOsN300i3TD4Vx"
    b"kf194GiD/lPrd5H1OnBUqTToD6eFbcijHfSZIY920GeGPOpLnxnyaAd9ZsijHfSZIY9X+syQ"
    b"RzvowRBtl5GrHJ/b5ZZzSHLwqV1GH1+L+LjaZVuCDy3Q7JcxYPWi/bIWMz1xIAu27mYNzUfo"
    b"cYaudBtWvBeNPwe1YtVsYErWea2NmMqK4plAL9KOs7yTtCXriSRaRXnLepD0e71oKfa9XuTO"
    b"kr7Ti64d9o1e5O4kPdOrWYkNs1bJCUuOUxT2je1RPIa0mFsLmPs5NDaJMeiFEJDRa63iEsbV"
    b"gXE1FSUrasZPE5IQDn07GgT9H5eRdeJeIl9c6X5hpFOl3k3CdO2u1udajT5BhgmCGT0UeK4O"
    b"DH6cMS9mRrJP+iO44WS54IbmY8+VoyszCDymd1TtFQNWgUKsL+9azivWtByqe5tWTXUwL6Bg"
    b"7hn2FDbso2/Y2V9LoylOYVdTFvD38o6zxJO8Je1GFp1U+1YzujH0C83o3mmfakb3TvtUM7p3"
    b"2qea0Ss4/1QzegXnO82ejTW05vfTWPOLH1VKKSP6NqAnGjf0kDFnkJ00HfThW1Jza+pN00Hw"
    b"EsJRWWNLxNoIyfrjsJ8/lfmf6tpX1/8EfSdIU2KifwH3mgchYlIp/wAAAAZiS0dEAP8A/wD/"
    b"oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+UKHQYkNlhBv/8AAABzSURBVGje"
    b"7dkBCoAwCADAGf3/y/aEVkKknB8Yhzodi8xcE+JYQwIEBAQEBKQS5xeHRMTr9SEzQ2mBgDRp"
    b"9t0mrlwKSgsEBAQEBOTJZK9MXRkBAWm+xu++p2UEBKR5s/9p2istEJCbfvXPDgICAgICMghy"
    b"ATE+E2lGp11pAAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icon_corner4 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAIC3pUWHRSYXcgcHJvZmlsZSB0"
    b"eXBlIGV4aWYAAHja7VhZlisrDvzXKnoJiEmwHCad0zvo5XeITI9l173lep/PWWXSJCkkRSAh"
    b"aP3vv0r/wSdU7ygmKbnm7PCJNVbfcFPc8TladnF/70/w5zN+7KfrA4+uYCOPn3md4xv60+0F"
    b"iWd/f+wnGaeccgo6H1wEBpvZJjvHlXjVbPfz+Zvq+V6Ld+ac/32efelonn9HgTNmgrzgya/A"
    b"weG72CzB/jk068O3NzfuvhZCyPhO4Y3v6Hr75Lzr3ZPvXDv7w6MryOVzQH7y0dnP6bXvtofu"
    b"NeLbzA8PQnPL3X/ufKc6i+o6rGsxw1OZTqMupuw7DOxwZdivZVyC/4R72VfFVWDiAGITaHZc"
    b"g7iyh2eVI09urLx2O3hAxeiXF7TeD2BgfSWIr34AAA7RLlYvoYZJoQCTAdQCuv1VF97z1j3f"
    b"4IKZJ2OkZwhjvPHloledn1xXQapGXWZXrr6CXt44DTUMOfvGKADCevo0bf/ui+544+6ADUAw"
    b"bTcXGNhcP0T0xDduhY1zwLjkIrljabDMUwBchLkTlOEABFzmkDizE++FGX4swKdBcx+i70CA"
    b"U/KTSYEN2A9wire58Y7wHuuTP7oRWgBEwhIRQFNDA1gxJvBHYgGHWgopUkopJ0kl1dRyyDGn"
    b"nLNki1FNgkRJkkWkSJVWQokllVyklFJLq74GhLBUcxWqpdbaGiZtEN3wdsOI1rrvoceeeu7S"
    b"S6+9DdBnxJFGHjLKqKNNP8PE8p95Cs0y62yLF6i04korL1ll1dUUXNOgUZNmFS1atV1RO1F9"
    b"RI2fkPseNT5RM8TiHic31NAtchHBFk6SYQbEfGQgLoYACO0NM1c4Rm/IGWaueiyK5IEaJwNn"
    b"siEGBONin5Sv2N2Q+xY3SvFHuPl3yJFB908gRwbdidxX3F6gNtvOKGEDZKvQfOqCIrBhUPMF"
    b"f4jHn7f0WwH/CnrdhpF1+aEj1Sl9OFm+UU/Ta+w9zpBz8an72EvOvZU5awkskoYDN5DFCxJN"
    b"n7mXqApGLuUiOh04G9Tg78pBVHm2oPZYqy/SxLIgKKqIz5O7n1LwkpPuREeIYPoIugp3pDCd"
    b"Wqh2G1rWZGvxzlzIctqwQcJ8Cq0zkmroaYGb6Z0kpGwIM1mnpIsc2ysckpw7ZDn3vTQ6FPu9"
    b"XnQo9pleU9Gy3TKC/3nz2/YUJGOwdmiqo8YwN1ZrIDjCIISG3IesPssJq3MXYGHLAe2kG7Im"
    b"HaSS4jtEtIrekGpFQJp+SY8lS2nTEkVtq86aYis5bZa1IRSqbJqBrwhcfk+LoYhbeXsvsp9w"
    b"19ZjzP2dW9nQZOGTk7FHglobsbAV5Ya4hTxkErHbSUFdQkisi5GCVpqrV1HpLUWYm3sP0jDT"
    b"KGnQWpIiNkDZtrHdLUWEVGSWtP2IFIYZj9tL1+uW/jTga8saQAZQRNUnh1AMS7STS3Eb1UJO"
    b"llybZofAHLqu2HjVPSw7c4t5LI+DRhBrpFxjbYR9IqdpU69DIt6CPH+TB58f8g7aQl7Fe5CW"
    b"TLF4MZqXKCl3G1zd6tvpeeOjDbl5IuNwQhLRkefBnhjafj5t8KoRSU+9VRTw0cnIe7p/0tL7"
    b"AT9jO72i+x3b0zJpAa7e0hALTZYXk1XaTZZYGNmSjKGQE8+IyNvccDFX6sHpaaMPR83DpxdH"
    b"AX6ZFmi/d/mfGUr8c0a+ZCgdFDVKbZKejJLNqDcMPRi1F65eGUoPFDVpxs+TnZvv7/h5snOz"
    b"HfykJ4JaBLh3lznLBD7w85Xb6eZ3d8+hbe5PGEk/oPBXhp78hDKFvlD0uzx7x0+Y98BQ+kJR"
    b"vgb3G0dfM/RhKdOLtbwZ+genf2ETfUO3H9GC3vHijhZ/xXB6DMKfM5xeBuEPGE4vTPk7hgtw"
    b"FpQqdS4fUIouQZZOqBFAtVSGdtCuoGLwec2Gil+AP4r94qSEBE10oMDRYvBHrzbVmtZtoXZY"
    b"dq0OG02rEYynHKug6Ng6sOwI5SWb0WVtKrfYlyk+XT+4FKgbA4fYXnVFbFv76ltYSSi2nNou"
    b"Ki0LtLOXY39UAcFNLbhmK0anZk9q4f6m1qHUqZLt64719agWaQ39WBbPakHYk1q2vrZiz2pB"
    b"Kbq569FbsWiZsjhjnQ0fVrDazU0kJKxSLHTAtWoIXiqqsYzdyKgejvTAeRWsdrAFWxX49k9L"
    b"2MLBffanC/ces79lEFR/VjLYyeJftLSN+XMs2pM/b2XudzK0if+BKc+W0KemPFtCn5rybAl9"
    b"asqzJfSpKc+W0I9Ngc4IXSBr8oqI00PIrbZEg3MNUT0SQOqQiu118Fgao83KPdW4sHIQFtu0"
    b"4423Bdukf6LEMkn0aYn1LI0uNelv9aJLTfpbveixVv5cL3qslT/TCyEoUFJuq6FvzJx52tlk"
    b"8dNzXb5Lwl/qKaK+841RBHqREHisNBCnY1t5nUcUSt9v6WzS91uZYydj8Rmr/6fHIutN4qaH"
    b"vWnSOO3oREucTa2ohVK5t5ariLQ8AraDGdXjGjDao1Lk7NayNYAqu6B4XMcicJaosNyvLq75"
    b"dLGu08WW3beTT8Bg8saLik8H9BZODvDnmbcuEi/yDmlvZJGBf8gy8HWDf0j6mWZ0Ue23mtGd"
    b"mb/SjJ6d9qlm9AKAjzSjd3D+VDPS99T4kWb05LTva9gXhyuXsxW6Hq6shb1VkOHz9Wyxtx0N"
    b"er8eLcoRDiofR4tYWnWOYkeLhGl12mqc1f8wZX/ZjfxKwL+Cvt9UgK+V/g9jXwgHtfXQsQAA"
    b"AAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAOxAAADsQBlSsOGwAAAAd0SU1FB+UKHQYkMl8s"
    b"e+YAAAB2SURBVGje7dlBDsAgCARAafz/l+kXjKS1JcPZy0RWJUZmjg51jSYFAgICAgJSqbm6"
    b"MCK2nwCZGXYEBOQnYV8NceVQsCMgICAgICAnb/YvjQBaCwTk5bBX5vPKoaC1QEAeDPup+Vxr"
    b"gYBs5NU/OwgICAgISCPIDbaDF2kDKN/uAAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_down_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"9UlEQVRoge3YOw6CQBRG4RM3gGBL4cZdhZ2JhZ1vKysLl4IFTCCEx4ijXMz/JZNQkOGeZkgG"
    b"REREbNsBp7GHCCEr1lfNvv2BX1GINQqxRiHWKMQahVijEGsUYo1CrFGINUNDVsAVSAPOkgJ3"
    b"YBtwz15r8guFB/0xPpcPabFXBmw+nu4NEbAvPvwElh3v9oVUIy5AHGZEf74xXSH1iCTsiP58"
    b"YtpCzEQ4fTFNIeYinAg40BxTD6lGXDEU4bTFVEPMRzhNMS5kMhFODJwp/zNZ7fnMCEfsUHPg"
    b"SBnh1g1YjDjXIPWYSUY4CfnxauqIHWpeLBER+T8vFihWmFWiZgQAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_down_left_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"yUlEQVRoge3XPQ6CQBRF4RP3IHH/OzEWhsJGCpczFkDA+MeM6NwX70leQQF5X6ZhwDnn3Po1"
    b"wAnY117kkxqgAxLQVt6luC1wpkdcgF3ddcoyQiUjVDJCJSNUMkIlI1QyQiUjVJJBtMCx8N35"
    b"9bQbnquVhslN5iTGSiByCMiHSCIgDyKLgOUQaQQsg8gj4D0kBAJeQ8Ig4DkkFAIeQ8Ih4B4S"
    b"EgG3kLAImCChETBBZP5iS0uzCXkSY2mFOfxq2c2Xv19yn3HOuT/oCq/olcDrAa3nAAAAAElF"
    b"TkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_down_right_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"v0lEQVRoge3XMQ6CQBRF0Rv3IIn734kWRmKlhcvBAhsCKMzHzPvk3WT6dzLNDDjn3F46A3eg"
    b"qT0kWgt0wJPkmCPwoMe8gFPdObGMUc0Y1YxRzRjVjFHNGNWMUc0Y1XaFaei/y9Fv8w24bjWq"
    b"tC1upvuc6kUxMhCIYaQgUI6Rg0AZRhIC6zGyEFiHkYbAcow8BJZhUkDgNyYNBL5jUkFgHpMO"
    b"AtOYlBAYv5rTQmB4MzKQC8NBpWeywx+HO+ecm+0NpQGU2ZDuCLIAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_pentagon_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"HUlEQVRoge2ZSU8UQRTHfwPjAi5xwT2SqBeXxMSDJ/VAMNGRGAQOIiae5WTCJ/ArGL6BJt7g"
    b"YEIMaozbQbxoPKAHLjBAxC1KQFDU8fCq0j2dmV6ruoc4v6Qz0+nX7/27q+rVq2qoU2dV0gFM"
    b"A0WgkLGWRBSBkjqmMtYSixwwgPMQ+hhQ11YFO4ARHPGf1KHPR5RNTdMGzCCCvwNXXdd6gK/q"
    b"2hxwPnV1IcgDN4HfiNBXwKEKdq3AC2XzF7gFrElHYjCtwHPKxa31sfc+9Bhw0K7EYLqAL4ig"
    b"D8C5CPe2IalZd8Ne4+pCsB5583oAjwK7Y/hpAe65/NwGmg1pDOQw8EYFXgZukDylXgMWlc9x"
    b"4HhCf6ECLqiA74ATBn0fA94q30vICzLOZuAu5V1gg4U4TZR32WFgqynnJ4EJnEHZZ8qxD904"
    b"c84kcCqJsxzSvD9x0mSlucEW7rS+gqTshqhOdgL3yX7i8s45j4G9QTfpknsGKSFK6rzNlsoI"
    b"uOecOURj1aWBu+QuIfm9JRWZ4fDOOVWXBtMeg1ost3OUv/CivuAePP3AR/X/jjKsNXTqB9F6"
    b"vZphlzJ+loKouOhMdsnPqAmZuf8Ae1IQFZVdSAZbxFOTefPyEpJ2G4DOVKRFoxtoRFaZP4KM"
    b"e5Gme2hZVBweIdouhzHeiLTMCrWVfrcjmpaR2q+MSlP+AtIaeeCiVWnR6EQ0jQLz3ovVapdh"
    b"9dttSVQctJZhXysPW5BisWIzZsAmpLv/ArZFvfkBMrCuGBYVhz6cJXVF/MriIfXbY1JRTLSG"
    b"IV+rKrgnHxurwbA040zScTY4AHiKNGmWg75HaXjiZxS04tJNmeWD6NixupVmH7JCnEf2stJm"
    b"HfBNadif1NkY0rQXkjqKQYeK/TLIMMxiPsvslShbeTmAvJXPSImQFnmc7yrGdm/0Fmm7KYch"
    b"OKtivg5jHHafKIvuZbRbaY7ifDpoNOm4Cg3ArIp5xLTzceX4tGnHFTijYr234XxQOZ/F7ve/"
    b"Ak5rDNoI4N3AS+OYDCsu8qZwyljZJCwgrTKB3TTcrmJMUaOfsOv8V/wD9srxvK1koPwAAAAA"
    b"SUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_pentagon_square_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"xElEQVRoge3ZTYsUVxTG8V+LiBJBcBQdiLpRBFEEFcWAm+gsXPqyUYkvn8ClGwVB0J3iQj+A"
    b"KzejgbgRXWnIqLNSFzMKAyIYlYRAENHEl3Zxb9s97VR3163qHpD6Q9FQVeec51Tde+651VRU"
    b"VFRUzAK1LtfrA1HRO930ZlI0kSPRRx2/FPRVSEsR42UY10xkPJ6bDS3JxiN4iU+4GY9P8dzI"
    b"gLUkGc/FaUH0a+xuufYzXuAzLmJen7UkG6/C79HmFoZnuGcpftMcaqv7pCXZeC/+wf/CG5nT"
    b"4d4ajuM9/sXBkrUkGc8Xhkkdk9iUw/d6PI62V/BDQS3JxuvwqEXIwgT/CzQfxAQ2JmrpSpbx"
    b"YbwVhsahIgEi+4Sh+U4YdjMtfKUmsghX4/kH8k3WbrQWi+tY3EVLLlqNt2JKevnshdby/Rw7"
    b"MrTkpo4TOIMP+BM7izjskZ0x1ocY+4QCiQxpthd13BDWgUGxNMZs1TCU4mi4xcETBTrPAtTw"
    b"tEXH8qwbOy1cL+PvfxgzOy19HX9EDfCqiKMb+FuYiINmLv7SbGuSqeNY/B3EJG9nV4x9VAmJ"
    b"DAnV41JhWfm5HGMvUdI6cluYM53mVNnMEUrwrTYtmTf3wqhQMban68rNT0LlHC3DWeMpLMNH"
    b"nC/DaY9cEFb4xr6mtBblrtA2DGI9qeEZ7mRo+YY8Y34UK7A5t6z8bBGayFKGFdOfwo9Cw3i2"
    b"LOcdOBdjrczQkpt24wdCy9BvJnG/i5Zp5C2n17BG2Kb2iw1YG2P1TN5EGmN2X067PDR8/1qm"
    b"05le56N49IvHeNijlq+krNSjmq+/bBrDNne1Sk0E9iTYdmN/W4zSyHqdE0IFK5txYROXR0tP"
    b"ZBmfF+r8ySLO2zgVfWa1QX1J5J7pe+kyj7GURFJ3fVPYhjea37mKUMMB4WvlVKqDTnw3f71V"
    b"VFRUVPSFL5FE0S7qGwl3AAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_right_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"o0lEQVRoge3YMQrCMBxG8ad0V3TtsTykJ/AODrEObh5AHL2AOugkIsUEEv++H3QN3xtaQkGS"
    b"JElq1BrYALPaQ3Il4AZs+fGYHjjyiEnAou6cPGFjdhjTjteYZd05ecLGDBjTjuIxE2D/PLDm"
    b"k4D5p6HTESHXkdF6I8R7EuIzbEQrQty3QlznjWhFiAiAA4V/PnQlDvnCGTgBK+BSaYMkSZL+"
    b"zR15m194agQJmQAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_square_border_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"7klEQVRoge3Z4Q6CIBQF4GNrPlQ9X1nvGb1G/UA2t+wKFxCB821tzTa5cBSRACKSDCvHPgnO"
    b"oRHV7ilREcWdhd+2Rjp0BH2p2u0iESfXyIe2JybVVSJOqtkp9PxeV0QzibAjRyPdI3vPVlvE"
    b"eppJhIiInBHAE8AbgAEwzceq84B9iC0/96IVKRnY4i8ArvN3k6uxPZ7sy+X50ZY9Xib8Xlq3"
    b"ohUpjbCdMQBesJ2o8mYnIkovZDc+977WP171NPPOLnVkQLkU1oj1dJFIVZrpSMhufO7ZLGqJ"
    b"31UiUf9bKKgS7iKRUq+lqnabSYSIZF/o3CVWfRkALAAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_up_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"8klEQVRoge3XsQ6CMBRG4RPjDurK4Kv42ro6qEGdmBxceA8drKmIKJZIL+Y/SROGAvcLCQRQ"
    b"Sin1p6VuDbopsHdrGnmW4FJgB1zcOgKzqBMF9IwYJGYC5NwGP+ER9+Pc7TFdCmy5DXwG5nhI"
    b"hsccMPxkEuoI8BCoY8y9AJoQUIWAYcw7BNQhYBCTABuaEfAaAlVM1O9MGwQ0Q8AApi0C3kMg"
    b"MmaF/zZkH/Z+gkAVswwZaBRykjuvABZAGXiNx0p3raLDTD+vzRPpnFn9twliLUGsJYi1BLGW"
    b"INYSxFqCWEsQawlirXEP91jTwz+7Ukop1aUrdgdXo/8Mk5oAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_up_left_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"w0lEQVRoge3XTQrCMBRF4YN7MOD+d2IHBXGkA5dTR4Eg/rRpa+4L90DpKOF9yaQF55zrpWmD"
    b"Z/jXsIed95923n9W5ck+gFPbcerLiHvxTk0nqixDjsCNwDeTIRAcU0IgMOYVAkEx7yAQEPMJ"
    b"AsEw3yAQCPMLAkEwcyAQADMXAuKYJRAQxiyFgCimBgKCmAE4V65NdPDVnJO7mTUZo5oxqhmj"
    b"mjGqGaOaMaoZo5oxqnWFKX+bL41nWV0CrsDYehDnnNumJ/0DldujWquLAAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_up_right_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"vUlEQVRoge3XTUoDQRSF0YN7MGT/SzGDDHQUBy5HByEQpNX+E2/J/aCpWfMOb1JFa6216U54"
    b"3+Gb7OEXB293PeJixkaSO+DVdfjbORzkfhNvOBoQMoVgMMhXCAaCfIdgEMhPCAaAzEEQDpmL"
    b"IBiyBEEoZCmCQMgaBGGQtQiCIFsQhEC2IgiAfL7FHlb+54SnvYZa2h6b+POKSKmIlIpIqYiU"
    b"ikipiJSKSKmIlP4FAp5tf55GdMaLwRGttZbZBwfblLXkvxCIAAAAAElFTkSuQmCC"
)

icons8_left_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"mUlEQVRoge3WOwrCQBRG4YMbmCzBrbsGS+1sfGDlAlxKLMLtBCEjucPlfJA2/AeGYUCSJEna"
    b"UAOOwCF7SI8G3IAZeCRvWa0BV5aIN7BPXbNSmYg4TkZkmjBiDBNwx4h8ZSKeLBGZ3+XX0F1/"
    b"6ybmf/ykxNEKJa7dYMyoSryzQonnezBmVOVi4gJ4JW/p1oATcM4eIkmSJH31AQ6pXcrw+RVm"
    b"AAAAAElFTkSuQmCC"
)


icons8_compress_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAHKSURBVGhD7ZpNSgQxEEZnpd7DlUtd"
    b"ewPXHsITeCfx/xe8kzcQtR5OQ1GkeyZRqC9DHnww0yjUo7rpJDWrwWAAB5aj3495HFrO1znl"
    b"QiX7ljfLh+WEC1lcWL7XeeZCBUi8Wqb/RyatM60iexYvQegMt1kKLSJIvFiiBB1Ko1akJEFn"
    b"UiWgRgSJJ0uU4Ho624qUJPh7CQnYRoRiHy2yErBJhGIfLF4CKSkJWBKh2HuLvATMiVDsncVL"
    b"0BlJCSiJUOytxUvQGVkJiCIUe+OuETojLQFe5N1y7b4TOiMvAV7ky30mdKYLCfAiPnSmGwko"
    b"iXxaeC6uKiOzH/lrzixp7IzIseXyn8K2edAdtK3UzpZwO6XBg1R6wFrCA57Gzojwsim9hJbC"
    b"S42Xm5RILSwv4gKwOxEk4lLcLwi7EEEiboroDEv0bkSQiNvTaSnOpqkLEYqNBwV+U9SFCMXG"
    b"I5u4PZUXodh4eFY6KJAWKUnMHdnIilCsL44sHZ5JipQkOGCekwA5EYqNkyKKXJIAKZE4syMM"
    b"XTZJgIzIND1tkQAJEQaMUaJ2UiQhwsiX0a+XqJ3Zydxa7EeQaZ2e8mOA6YcB6acddCZtjj0Y"
    b"yLBa/QCFElub65nNHQAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_enlarge_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAEVSURBVGhD7dldCoJQEIZhr4r2EBHd"
    b"d9Xi21VELaDOCwki/hznTMcZmRe+i4SEB8JEmyiKomhL7dJuyjukVe+U9lHeNa16m4Ec0x7C"
    b"vdLMQKTt0+5priFTCOYCMoTg87vz2TxkDMHxZ+eYacgUglxA5hBkHpKDINOQXASZhSxBkEnI"
    b"UgSpQbiLvfx25oAwCYLUIHy5PREnlSRFkBlICYJMQEoRtDpEA0GrQrQQtBpEE0GrQLQRxCW/"
    b"vfzzVyAuF/IPhGo5EPMImoO4QNAUxA2CxiCuEDQEcYegPsQlgroQHs24RFAX0p8bBI1BXCFo"
    b"DMKD5qEH0DnjAXf1pn5a0vHKoXqbgfC6a+g1WMmK7mKjKIoiQzXNF/nEYloeaSPOAAAAAElF"
    b"TkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_rotate_left_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAANgSURBVGhD7ZlLyA1hGMePO4Xo27gU"
    b"uSwkt5S7FDbuC5KiWLmVz20hsVZkoSgLOxulSBELt40Fio1yXZDLQoqk3In/75x56u0035mZ"
    b"875z5pyaX/06c55v3need843720qJSUlhTJTrq8ddg7T5GE5uvqtxmn5r3bYGZyTJIxbCUQk"
    b"NeSEvJFBzg/OoOgTtkhryCUCEQflg9phLHeklUsj5wdjmDwvb8peBER/+Ubek3sIpKSwhgyW"
    b"L6RVvFkaQ6PPLDRqyFm5rc41MhhHpF3sAgEP3Ia8do7xq1wmg9Iv+gT+nbhbh6JjH9yGbJLd"
    b"8qcTozFzZBBGyGdydfVbWNyGbCQglksaYPEPcoz0gjtOt0eFf2SWBzkNcQ2BpdL9ZW7L3rJp"
    b"uBNvpVW4W4akp4bAdml/wx3SC3ojBjZ3fAhFo4YA17S/v5dDpDd9os+QJDVklPwi7ZwDMhMk"
    b"fUbOqn7Lj6SGwDFp57yUmZ4Veg4rfI1ATrhzrSUEYhgpf0nLZ7FMjU320HfQC4H1nHicQFoW"
    b"yVPyuezpJ28l9FjWkIcEmsF39A4BCzRryA/ZV3YkzK7d52SiTGSSPBq5l0CbwDhiDZlPIImV"
    b"0go8ItAmMN+zvOhVE3Eb8phAm/BEWl4rCCSxUFoB5lntwjtpeZFjIjxIVoAZLw9a0QyU5GJ5"
    b"jZOJ0LW5U2i2eYpmhrR86H5Tz/vuSyu4i0DB0HtaPncJpIWu1wpeJ1AwLKwsH/YMUjNXWsG/"
    b"0nup6cFYSQ6WT+YZudtv57LDlxLmfJYHXXBmdkqrgM0A7kyroXf6Li0P9rYyQ5fnrtevyFbC"
    b"ZJW1kF2ffa+mh4IN0ipC9p1axX7pXnut9IJfwipjfMljf6setkbdATDIxkeXdLczeV5Wybyg"
    b"bneD7pUcLoMwVX6WVvlvySAVctFFXfskddt1uCbXDso8+UnaRfCqTDXvSWC8dB9s/Chny1yY"
    b"Iut3zb/Jk7KZ7pkylKUOt062fSbLXOGZuSzdCyOjLy9/2B+eLgfIeogxAeScW9Idsc2LkpdJ"
    b"LYO3tbylqk/EpNdhHGI0Ro7jEjf5pdfJQuAOMwN4KuOSSyNlGbHbYd1ThRcyzEx5j8iaIS5p"
    b"5G+cw7l5b8l6w8JngmRJyuszXCDpnfLYDC8pKWlIpfIfTyNhWWO84TIAAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_rotate_right_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAANbSURBVGhD7ZlLyA9RGIc/d0oiC7Jw"
    b"T5Jbyi2ykOS+ICmKjegr95VYk4VSFFmyUIoUodxKFigLKdeFexaKWLgTv+f/n7dO03zN9cyM"
    b"mqee/uM158x7vpk5t+loaGioBavltPbh/81febR92GKo3Csnt/7lmUPyago5vyvCDdkoieEp"
    b"Aj65Je1iSeT8rrgnd7cPW5yTVm4DgYB+wW+hFNmQMNvlHfla9iYguslr8rQcSKAoVshNIU/K"
    b"qEZgmoYYA4JfWC+trmeyv/TCMvlFusm/co6zNMTljLS69hPwwUz5Q9qFON4i1zmxvA3h0doj"
    b"TwTHRq/gNzcj5XtpCXNXFkpYK4tqSBTL5RNJd52LHvKmtGS5E/Ol4bMhdAi/JXXTCbh3KTU8"
    b"PpYo0v+7+GzINml1v5HDZSboUdxHipcxjO9Hi/GGgdTt3VLDAGZJfpbDZBjfDeHRzkV3+VJa"
    b"kgdkFL4b4jJdHpepGrdAWoI/5RAZBS9+krlWXi5Jy2cxgaQclFbwMoGKcQfLYwSScl9awc0E"
    b"KoZH+Kk8IucRSEJPyeNkDZkqqybTGDJOWiMYAAubIpTNXGkNeUegJuyQ9J44nkAc9ArWkMcE"
    b"asIDaXktJRAHJ1mBhwRqwiNpeS0hEIf7aDHHqQtvpeVFjrGMlVaA2actRaukr7SZMI6SsdD9"
    b"uouoUrZsYmAIsHy+y8TTlLvSCjKVrxp6LMvnNoGk0MVZwSsEKuaGtHz2EUjKLGkF/8jMi5oC"
    b"GCHJwfJhFpwK1spW2OfMNg7mV5YHXXBqOqVVwIYDf5myoXf6Ji0P9tZSQ5fHOGKVXJBlwkTR"
    b"XYewh5Z5KFgjrSLcKstil3SvvVLmgjthlTG+sNfkG7Zr3QGQTYjcDJbu1ijvC9unvghvzb6Q"
    b"g2QhTJKfpFX+SzJI5do0C0FdOyV123W4JtculNnyo7SL4EWZaN4Tw2jpvtj4Qc6QXpgo3ccM"
    b"v8rDMkv3TBnKUodb53M5QXqFd+a8dC+MjL7s0bJnO0X2kWGIMQHknOvSHbHNs7LQDz1x8KWW"
    b"L07hREx6HcYhRmPkOCpxkzu9SlYCf2FmACyJo5JLImUZseuw7mnBxyBmpnwbZM0QlTTyf5zD"
    b"uakngGXDwmeMZEm6KHCOpHfKvTHd0NCQlo6Of9ewYWPOK1cIAAAAAElFTkSuQmCC"
)

icons8_choose_font_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"RElEQVRoge3ZvWsUQRiA8d8lQYyIH6CHBCsV/ACtLMQqEBQrMYpGxcpSELT1T7BSBFsbKytR"
    b"o1ZCCkXETtRgEwlpVBANKDGJOYtNuFxmL3u37N5eZB/YZvZl5nl3bvbemaWkpKRkLVHJqJ8N"
    b"OIgq1sfc78FCBuNMYwwzGfTVwDGMYha1Dl2jWSawCfc7KL/8+plVElWMF5jEtSyS6MfbFZ1P"
    b"4QYOYfOy2G34uyJ2YfFBFM5NjWLPsLVJ7BnhE33fAcdEdmFOXeqNaIaacUeYyN2cHVvitrrQ"
    b"H+xNiH8nTORcnoKtMqUudC8hdrtoPaxcHzvyFGyVCXWpowmxZ4Wz8TFPub42YodxBS/xKiF2"
    b"MKZtrI2xuoYPwhk5X6hRCqrC9VHDQJFSaRgRJjGe96A9OfQ5GNOW+/poZ7GvxgCOoBfHY+7X"
    b"RG+yZuRWnrfDTnzXZeV5Gk7osvI8Lf14hHldUJ5nQR++CSWHipRKw5AwiR9Y14nBs3z9nopp"
    b"W9rPrxkqmBTOyEiRUmk4LExiFls6JZDVT2s4pm1MtEbWDH0aN11L19UipdIwLExiTpfsBtvh"
    b"uTCRx4UapWCf8OyqhtNFSqXhqTCJz7KrqjPhgGh7uqfJ/Yvi66brHbFrkcvqReCcxvOoiuiP"
    b"bkaYxKTVD+06zleNgr/wRHREOiF+Jmq4UIRsMyr4rf1S/EERsknc0l4Sr7GxENMEekXHoq0k"
    b"8VD04aeruYRPQvl5vMDJ4tQaafVj6H7sXoz/Ijqnms5LqqSkpOT/5x8uy2K2p2FyYgAAAABJ"
    b"RU5ErkJggg=="
)

icons8_level_1_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"mklEQVRoge2aO2sUURSAP6OFidkNG2MSBOu0EUERhdjbyZLSTiWFhSCWoiDoT/CFjb1/QAQf"
    b"6xIbFWOTgCDEN2wUjYXIZi3ODutOzszunXPnUcwHp8jd7LnnS2buawZKSkri2OE53xSwABwE"
    b"5oB9wHj3s03gG7AGvASeAC3P/ZuoAktAE2gDnSGjDTwHznVz5MYEcA34zvDFR8UGcJUchBaB"
    b"T4bCo+IjUM9CYAy4l4JAOO4Ao2lJ1JBrOm2JIF4gg4dX9gJvM5QIYgWY9CUxBiznIBFEE0+X"
    b"WRb3xKC4bZVYLIBEEIlHsyoyHOYtEMRnZO5SGYkRuQTsd1KP5h1wBbhoyDELXHD90gT2GfsH"
    b"cm0fp7emO2nMuYHj7L+UsKM28BA4DexR8lpFOsjabGiaCTs5MyCvD5GGlli7R6aAI4NdVf6G"
    b"fq4lzBPHUZRJUhM5EdE+LAeA88Aj4L0hTxQjSI197FJ+cd7QyXVght7N/duQK4554MH/DZrI"
    b"nKGDWcN3XdhWo3YJzWRQiJXpcIMmMq60FY1tc4nlpi4Umshm5lW48zPcoIl8yaAQK1/DDZrI"
    b"WgaFWFkNN2girzIoxMrrcIMm8hjYSr2U5Gwhp5R9aCItZI9eVJrIcr6PqOH3frq1mHCqrYpY"
    b"W5fc4aHcuoxvARWt4J0RIn+QY6CFodV1OsgJ/KFuHAMOG/LdQDZuTlSAD9j/K75iHcPyqV4A"
    b"gSBOJZUIuFsAiZtWCZDjyqR7eB/RAHb7EAHZI6/kIPEGj4fYATXkr5OVxDIpPFYIGEUewqQt"
    b"cQuPl1McddIZmtfxMDq5UkHOc32sAFrAZXLeZleRY8wG7o+nnwFniVh2uOD7hYFJ+l8YmKZX"
    b"5C9kubKKvDDwFGUVW1JSkg7/AOZX0ILb/Rs6AAAAAElFTkSuQmCC"
)

icons8_keyboard_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"nUlEQVRoge3YMU8UQRjG8d+dFDQqNXcUJkhICPYUFvYW9tR8D/wMFNpbGUKFFlDpJyCBykQb"
    b"a0/uiLHCLMXsHRdzkNu93M0smX/yZu4mO7vPs7P77puXTFo8ii1gAm08w1P0I2uZiS4K/Kyy"
    b"qD0fLTOxUo6XVRalaGS7HH9UWZSikdfl+DWqihl5iWv8xWpkLbVYxz7+CC/626hqpmQTezjA"
    b"F+GlLsbiHVqxxE3DlvDcFxPiN47wqu7JF+V8Byd4jAFOcYYLnKv4zYjFMr4Ld/4DnsSVU59d"
    b"wcSZOZZEi/iOvCnH9/i3gOvNjW/CjrxYxMW6OMSVyVklxbgSMt3zcRO9BITVjR46yp0ocDyc"
    b"aAgdfBK0f+T2cWqSiSFrgvZ+q/xB4mXBPRSkWcbXYumO+eK//61E50c8mB3JRlIjZ63UmDZr"
    b"jRMrU006ZsSD2ZFsJDVy1kqNedVaVcm11pBsJDVy1kqNttB8ILSFmsZaOQ4ITa5CaK00yUwX"
    b"nwXth7CBX+I32mZp0K0P3XWEJtcgAWHTxqDciZGJTCaTaQ43WK8NPKELVSYAAAAASUVORK5C"
    b"YII="
)

icons8_roll_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"60lEQVRogd3a3Y9dUxgG8B89M1PpHKLtuBEqqSolbXzFx4UIE8y0IxE30vi64kJk2rpF8R+4"
    b"J5qQ+A+4QLSIdlAXbWZ8lUjRb0GHpF8xLtbaWVv17Dnn7HXO4El21snJ2s/7vHuvtd53v2vx"
    b"P8F5Gbkuwl24HWuwEiMYxhyO4xd8g734FO/G/xcci7ER7+CMILiT62S89yEMtGFvCjtzOnAB"
    b"NuHgWaK243k8ILyVpRjEkPB2rsGDeCH2PV26/6fIOVhht+ibBWP4vkT6GZ4UhlanWIonhKFW"
    b"8H2N+1r0z+LIYrxSItuN8bqkJYxjOnL/iZejzTJqO3KpMDnn8Ae2YFEdwhZo4BmciLamhCFZ"
    b"oJYjK/BtJNiHtV3LbB/XR1tz+CpqoIYjgyXCXbi4vsa2cYkw/wpnlqvhyFAkeQ8XZhLYCZrS"
    b"kN4l86rVb4wIK1k5/vyr8aH2A+k/0MgsZh3uxq1YjcuEFAV+x37h6e4UhuuezPZroSksxzM6"
    b"T1GmsVlydkHQiCJ+loQdEILmI7gBy4QcakBYdW7Eo3jV39ObY5iUf4TMi9X4vCTkfazXWZBs"
    b"YAN2lHh2Y1VWpRWYEFLvIi+6JwPnmBSvjgsPpad4WMpYt2FJRu5hvB65TwufBz3BhOTEc70y"
    b"gq3Rxil5k1KEcftbNPBsbvJzoHBmVpiPWdCQJva2XKRt4A3peydLpr1Zmtg558R8GJYWgKfr"
    b"kjWlOHFvXbIuMB5tH1XzIW6R4sRC4YOoYVMdkiLt6Pm6XoGJqGFvtwTrpLSj76lDCQ0cilqu"
    b"bdXp/AqC0di+JdSsFgpn8Hb8PdqqU5Ujt8R2Ry5FNbA9tre16lDlyNWxnc6lpgZmYttVcDwm"
    b"jMtl2eR0jxFpGe4YJ+PNVSXMfmFI0HKiVYeqofWfQpUjs7Ft9kPIPChKUbOtOlQ5ciC2Kyr6"
    b"9AtXxPbHVh2qHPkittflUlMDRSD8slWHKkemYntHNjnd487YdrXJs1ZYKQ5a2BRlAIejljXd"
    b"khT7FRsyieoG90cNtYp5xUfVQqYpH0UNk3VIhqUIP5ZBVKcoUvgjMnydTkqbPP0sbTbxXbT9"
    b"VA7ChlABnBPqTv3Cm9HmJzJu810plYO25iKtwEtS1TFbOajAeqlA10tnXpQKdK22qWtjYzQw"
    b"J9Sdcs6ZpjScTgmnIXqKcWmY7ZOnrDkhTexf9fBNnI1V0o7rnFCymdBZBjAgBLsiThQTe2VW"
    b"pW1gkVABPFoScgiv4THcJGzuDMZrOW7G40Lp9XDpviPCEtuLQwhtY4lQPCufJ2n32iPEqdrB"
    b"Lud5LUK6PSqc2boKl0sLwix+EPbtPxbOas2cg6Mr/AVMUjVunZJoRgAAAABJRU5ErkJggg=="
)

icons8_console_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"ZklEQVRoge2ZQUoDQRBFXzS4iIKCEoILA15Br+LZ1Ft4A0UlCyEuxGBUBPealTsXaRdd0UEM"
    b"2tPlTE2oBwUNSVf+o6fTMwk4zr+xBhwBEyA0rCaSfRXg2ECg3DqksBJ78xfNLPvE7K8tGQC0"
    b"6suTRQBYqjuFFi5ijeIeaTQLsyLtwti/tSzgItZwEWu4CLAsZYbZPX0qZ8A9sKuaJp3P/GVF"
    b"TmTeM9BXi5VOtkgHOKV+mWwRiM/K5zL/AdhWiZaGigjAOnAlPcZALztaGmoiABvAUPrcAFuZ"
    b"/VJQFQHoAiPpNSTKVUEAguaBOAXeZdyRqhSNFekSL6kA3FHtple7tHrArfQY0dDNvgM8yvxr"
    b"qt3kM7JF+sATX5t7Uy1aGlkiK8TTPAAD4lny/fVxoXdKXZQRaf/6tp+ZAi8S9gB4m/MBZSg1"
    b"z3/7tYaLWMNFrOEi1nARayyMyEL99XZZdwgFUu+YHeevfADs2tPOHBgeRwAAAABJRU5ErkJg"
    b"gg=="
)

icons8_text_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"3UlEQVRoge2ZWwqDMBBFr6WLq922O6nuo/0xICGayftS74EggsnkYDIfM4AQQvwjbwAbgG/n"
    b"sQKYa4qMkHDjU1PELdobc9xH4410I1dkge1YLIVzzEzG79zvnbz3lBglc6L7fCYsfhUwxNnG"
    b"c+ZEud0d2fbnMYtUTYu94sz7gsfc/orM8VOnJZXmxGlOjkg2t7sj9EiEDYmwIRE2JMKGRNiQ"
    b"CBsSYUMibEiEDYkE8HsoZzTrfdQi1EOJFbFbFPmKSa1bVa1z6Y4E8Ou2sQGQHi2/bmvpDQ6v"
    b"6wohxBh+1Qai3Sp+mhwAAAAASUVORK5CYII="
)

icons8_info_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"7ElEQVRoge3ay29XRRQH8E/1Z/sjoNCWAkuJT9RU9gQfGy3BBZpoouIOgxseQbfq0ro1aeI/"
    b"YogYRRCNVUTdWAvoRmuiCTa+KgTNdTFzM7e1r9+98/sVEr7JzUlm5p7HnTlnzpy53MC1hb6M"
    b"vIbwEHbhPtyBLVgf+//Cz/ge3+AMTmM2ow610cYLOIF/UXT4/IN3sR8DPdYdrMPL+Kmi1GV8"
    b"gFexDzswiFviMxjb9uE1nIzvlO/P4JjwcXqCvfiuosDnOICNNXhtwos4W+F3EXuyaLoE2ni7"
    b"IvALPJaR/xi+rPCf0IXZ2SYoXghOewg35xYSeR7BnDTbW3Mx3y5Md4EpPJCL8TIYxXSUeSHq"
    b"0AgjFYafYXNThh1gUAjRheCT2+oyakvL6RNpP+gl1uNTaZnV8pnSsaeEza5T9ONNIUTPYDy2"
    b"dYphaVVMdPryXsmx6/rEuP9vgOM1eY1KAWBstS+tk/aJQzUFE2ZhoSEzDfgdlZx/VUvsFWmf"
    b"aBJicxvSwleRz9GVBreltKPpZrfY0nqjIc89kc+PVsjN9ksRoin6BWNmNHP2KvqkSPrccgPf"
    b"i4MONBTYTRwUdDy+1IAhIa2+rF4C2CsM4gququh5U2XAw4Jzf4zfeqpaZ5gVNsmWcJDDfEN2"
    b"Rfph73SqjZOR7i4bWpXOHZF+nUFQsUR7rqN1qeO9ZUN1Ru6K9EImYd3E+UjvXqzzkvAl6+RV"
    b"S2HhPpILmyO/XxbrvBI7m8b6KrplyIBUJ8D8pXVdo2rIn5FuWAtFOsRtkf5eNlQNuRRptjNy"
    b"F7El0l/LhqohZbRaNBJcY7gn0jJ6zTNkKtIHe6ZOfYxG+m3ZUDXkTKSP9EqbBng00tOLdQ5K"
    b"SeOmTAK7EX6HpKSxdPp5MzKL94UY/XQmod3AM8Jed0Ilai3E88KXO5tJaO4Z6cO5yOvZ5QYO"
    b"CMfIAo9nEJzbkCcinx+s4hriWBx8TvP6bk5DWkLWW+Dwal5oS7XeIzWFrnTBUwflB57WwaVQ"
    b"Wa2Yk2J2J8htyE78rWZ1Z0L6AsM1hOfCiJB1FHirDoO2UBYqhDPyWhSxN2Ay6jCpwT3jiJAG"
    b"lNcKIzm0WyWGhEJIeR3XOJndLk3ttN7kYjsrMs/j9lyMt0rLbE6ovbaWfaMeWkJ0Kh17UkrZ"
    b"s6EtBYBCKCjnun3tE64yyn2idOyu3r2PSdNeVu0PCklnpxjCS1LaUS6lnLfFy6ItLK8ynSmE"
    b"jPQUXseTuF8I2/3xGRYujZ6KY05JBY8y7Thsjf6AGBCq4seFI8BKG+HC5yreERLARgbk/Klm"
    b"o1CL3S1ULe8UwvWtsf8PoQ51UQjpHwmzsmQqfgPXM/4DBaQ+gHlAM7wAAAAASUVORK5CYII="
)

icons8_laser_beam_hazard_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"tklEQVRoge3ZT2hdRRTH8U9erEltqjFtasVKg1i1GEQSja1VidQuRFCx+Kc0CCpmY6UWq6iI"
    b"IqKNGmiLLYhQXUjRTV0ItouCiEihLvwDQguCqFijdVNcCF3pYs7z3b7c/LkvuUmE94VL5s09"
    b"c+Y3c8+cmXtDkyZNmjSZB1pK9n8B7ovyx/i7rI7KHEgLPsNf8XspNuKfEvssha04jkpcx6Pu"
    b"f8US/IL16IprfdQtmUddhXkFB6P8OnZF+WDcm3XKWCOr8A36sRzXSqF1AqfwLW7AzyX0Pat8"
    b"hJekSdqjtkb2Rt3L+HDe1E2T7DrYglvr7j2Exfip7t6CooKv1MTuyrF5S22QX0ebBcejOCaF"
    b"z7NYnWOzCjvD5gs8MmfqpslS/IoBXIZnJrF9ThpkH37DhaWrK8AI3ovyGybfK7Jh9778EJwX"
    b"rsCfuBTrpPifiq24BZdE2zWlqSvAIbwgxX01xWZZhw11dVXbSrQ9VLLGKbkdP6IdD0trpJ7B"
    b"uOrpxxDOxw/YVIrCadAq7dKb0WF8rFcHNag2kBvrbEai7ebw1dqomJnk8cdwRgqLbdgnxX5n"
    b"3G+p81/J/O4M27fxZPg4Ez7nlIswhuvRg6czAvfF3x4Mqz2R4ajL2oi2PeFrLHzPGaN4N8pv"
    b"Sim1Sif2S/vEYSl8RqLcF/c6M/aLpR1f+BwtTXUda3AaK3AbHoj6fmld9EiCD0hJoEp71PWF"
    b"zUC0gfvD14rwPSfp+BPpmFGRTrfZdNsihdBhtOW0bcORsKlvVz0p74w+ClH0fWSTFBq90mL9"
    b"Dn9gbZ3dRjw/gY9RaROspxef4wN8jydwdLrCimSt87BbmrF2XCmdYIvSgotzrlPSRLVHH7uj"
    b"z1knO0PDWJljUzF5aLWrhVbeJK7Ei1E+Gn3OKl34XXr8EzEgbXjVk+0B5w6mTW2xrw7bvJPA"
    b"U9LT7o0+u2ao/Rz2SmsDXp3Ctmj6radNLQXvj75nhbXSgl4mzeI9k9g2siHmca+UMJbJTyYN"
    b"cQTbpXNQXihkGcoIvElaB4NxVaJO2AxN4WtP9Lk9NMyIu6TPOIvQjasKtM07NE41EVmuw+PR"
    b"94nQ0hCLcBJ3NuogGJR/jJ8Or0nhdYd01M/LhFOyA582KCDLBuNfrKZLt/SNTGjZUdTBcunM"
    b"c02DAmaTbbha0nJa0jaOiXbOLVK6PImbcXcJAovQjS8lTQ+qbQX/MdFAxqRvUB3St6pjJQks"
    b"QgcuV/BA2Sq9G5yV/jGzEK6zeMcMXoebNGnSpEmTifgXBxu98dH6sbAAAAAASUVORK5CYII="
)

icons8_laser_beam_hazard2_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"WUlEQVRoge3YWYjVdRQH8I9LLrhNmaZCIGUGFUVE0EMPLVBSYqmUlLb4UBhKaRYYvlgYVE8+"
    b"RDRWPggVGi0+FEVFRdIuiuWSLRCVuaSR6Tg5zkwP59zu9XqvznJnRuF+4XAv5/f9nd85v+X8"
    b"zu9PHXXUUUcdfYB+PWz/fCzI/8/ipx4er0dwLprQntKUutMO60UAL6W0p+60wtVoxV+4Htfl"
    b"/9ZsOy3QHzvRhrloTpmbup3JqSkG1NogHsDt+AGDcYlIKs0YhInYg697YOyaYQQO4SimixV4"
    b"DEvy//RsO4RRfeRjh/CiONRvYCP24QwMzP+b8HpyVvWRjyfFeWjBYdwpnL2ppP2G1M1JTgsu"
    b"6GUfO4SvhKNPiNnfXIGzOdseT+43tRq8VtnjWlyB/TiCM3FbBd6MbGsRAV2OG2vkQ7cxALvF"
    b"YZ4jAnn1BPxXknOvuFf2iDPU51gkgtiCNfgXDSXtE1MKaEjOa/hObLHFveLpCdAgaqgWzBQB"
    b"lTv1BT4v0y1O7szs2+TY4HsdL4sZXSNm90/Hb5NNKaUYgL3YLrZhe9rqE0xWnM2705lbs20s"
    b"vsUYxUDGpG5scqZln3sUV3VyL/l+DDalI0tFQbghHVqJYdglDn8hkDtSNwyNyd2QfZemrfKV"
    b"63FMERlnr7gT2jBJHPx2EcwqHMTPKQdTtzI5i7JPW9rYmzan9FYQA8VZaMVssSVWYQLGlQTz"
    b"a/62pZTqFiV3QvZtEavXqvI56xEsSWc24k1R1Y7E+/gH72FbOjUfQ1LmZ0Db8G5yP8i+zXgr"
    b"bbbnGD2KsxTrpBk56PxsG4prxDlox8MV+j+SbbvFY2to6hekvpCOD+dYPYa1OeBqfJ9OP4Nf"
    b"SqQQyOgK/UeLVWmuIK1pc3X2X9sZxzpTa10kVuEwPhKpsvCA+rFEfk/+oAo2BotHVquY+VJp"
    b"Spuf5BgzcsyaY4uYzYVi5spv6/GYJ2a3HSsq2FiRbc3iJTm+rP0z/I1HFcuemmJaGt6FW8RK"
    b"DC7jrM/25diaDjfiwpTnU7cVTyb30zIbE8VqPZXtbTl2TTBIlOetmCW2wdMVeEPEa7BwT3yp"
    b"+E2rvUy3MrmVtt9zOcasHHN/FV6nsazEieXiYhtehduoeE+sFm+O7Sn7Ule4Zxqr2Bguzss7"
    b"ioEv624QY8R+bhFbqgVXVuH2E2+Lh0QlewBTFUuUqWISRiVnj+qfbO93bDpuTl+6jHVp8AVc"
    b"KlJiR74XN4jLcoRiICNS15FyvR9+E6VN4YPGuk76/j8uVvx0M7KrRlQu4zuCq0QA94mVPIrL"
    b"uuLADpE15nWlcwk+FKVIV/CxCGJh+rKjGrFacTZVVKZ/iBWp9EWkoyhknK7YGJZyTvoyCTfj"
    b"7XJitZt9ttinD+r+Z9UjKV3BIfEY2yYSRD/xrjkO1Q7uHJEqD4qL6VTAOJGa79KJZ3F/UY4f"
    b"EZfSqSBHRPlfcRedLJWerXsZq5Y4IB5dddRRRx11nDr4D2aAfaSIazOLAAAAAElFTkSuQmCC"
)


icons8_about_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"cElEQVRogd3aaahVVRQH8N+7ms/qORSvjMih8EkWFWI2SoVlUERBaBEFCpFgZUESBRVaRBF9"
    b"qQ8OfcuywqCiAQoqo5kmQiuTnLCQcMjZetXT24e1r+e+x5vuved6n/3hsM85d5+1/vvsfdaw"
    b"1+V/gqac5AzBZFyMc3EGxqEFw1KffdiLzdiAVfgS3+PfnHhUhWbMxApBsljlsRvLcQMGV0um"
    b"mhlpxb24A6PSvSJ+wBf4DuuxUQxwX+ozDMPFbI3HBbgEZ5XJ/g1LsEjMXl1wLB7GHtnb/Abz"
    b"cFoNcsdhvngRJbnbcLcaZqgnXIq1ZYrewkV5K8E0fFim52ucnYfgJjyIjiR4FabmIbgPXCsM"
    b"QhF/YXYtwo7BS0lYBx5N944Ujsdi2ew8rYpvulksnyJ24ZocCVaK2WhPXBarYDBNeDU9uBXn"
    b"1YFcpbgKBwSnp/r70GPpgZ1y+tBywpX4W3Cb1VfnK3AQ/6QHBxpuFwM5gLaeOh2HTanjIzkp"
    b"PkmELpPTeR5YJjh+qofv5aHU4Vv5OaJyq7MoJ5kjsSXJvLnrjyfIPPblOSkkwo3SQJbkKLe0"
    b"xNZhEBTSD7NEHPQ+Ps5RYbGH81rxvBjEeOE8D2NNUnR9jsro/I205iz7PsH5ndKNCenGdmma"
    b"jhK0ioijHS0Fmdd+T5jeowU78JWIQqYVxLTDJw2jVD1WpnZKQea9f6yDorkiQtiJBXWQX+J8"
    b"9mCcmi421UHRKGHa4ZQ6yN+Q2jEFjEgXe+qgqN7YndoRBZkX72gQmVrQntqhBZ03B442lFbT"
    b"3oIwY3Byg8jUgpKT3VXAz+liIOUe/UWJ89qC2FCAKQ0iUwsmpfanAj5IF43My6vF1aldWRD7"
    b"r3+IPdsJDaNUOS7EGJGbrC4Is7ss/Xhno1hVgbmpXa4sRWgTA9orX+u1UH0SqzFi4+6g2Es+"
    b"nFitw4vClyzMUWG98DiG4hWxWd4Jo7FfzExe26IL5D8j03FIzMjYnjrNTUo3yYK9WjAWc9Ix"
    b"qY++/UErfhUcH+itYxPeTh0/EknLQEGzyJmK+Ew/stnhIs4v4jVRVms0huB1wWmzClKC0aLq"
    b"VBQpcCMDyhbZKtmBcyoVMFo4yiLuypVa/zFeVsnaJpx2xWgTdrpDbaW1atAkDESpyLoWZ1Yr"
    b"bIUu+0ZHCNNFbbJktpeJ5VUVbk1C2h2Z8L4Zt4i4rzSAzbiuFqHTZRWiXm11Nzixgr6n4za8"
    b"LHLv8orufOG5+42u2/IzRajSjKWywKw3tIi3OQfnC8uyRoQO+0Utg6gJjhSxUZvOZYZSqfu5"
    b"NLB2VaJJxFiHktBnZXFYdyjgMhF2lNfd/yw77+vYijdwj15CjUoGMFhUb28SFup+PNNN30GJ"
    b"/AzcKHNKRbHjtxRvihmaKJbOCJkPOiCs0MZ0bKmVfFc8IStBzyi7P0Kkv/NEcXSbzm90PZ40"
    b"gJKxz2XkOgTh7bpfDr+IgecRAOaOqXhXhMXlpA9gNV4Qf6CZ2CiC/UG51RoiLMtwUdX9vSGM"
    b"qsR/ME41xQZApAYAAAAASUVORK5CYII="
)

icons8_align_bottom_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"oUlEQVRoge3ZTQ6CMBQA4afx/ldygZ4Ldi4MSX9oH5NmvoSVUjtAgNgI6RbviNg7ty1zoo/C"
    b"5/vk8Yd5VX6vdUJXD0CzZ/YPzmIIjSE0htBkh3xj0ptC7ZO994H4v9+0NwUvLRpDaAyhMYTG"
    b"EBpDaAyhMYTGEBpDaAyhMYTGEJplQmoXQ9MXN1uVzsjnwthn/56PHk9Yo9cvsv3mv8xdSzQH"
    b"L7opUXxgNIwAAAAASUVORK5CYII="
)


icons8_align_top_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"qElEQVRoge3aTQqDMBQA4Vi8/5HcWM+lC7GL4B95Eqc6H3TRheENbVLQpiSWJns/3jJFud/8"
    b"nzun0Jt1ad43Ja9+Zb0hsN53b9B8s+eim//qw2Rz3ja6wIbqp99jTi1DaAyhMYTGEBpDaAyh"
    b"MYTGEBpDaAyhMYTGEBpDaGqHDIFrd+/GH1lu6de6rphfLRpDaAyheUzI2Yeh+L92HH0ikV/T"
    b"tefs0r+ZAAn6K06SZpqKAAAAAElFTkSuQmCC"
)

icons8_align_right_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAGYktHRAD/AP8A/6C9p5MAAACgSURB"
    b"VGhD7dfLCoAgEIVh6/0fKip6rS4ys0hcWAs92f/BMAgRHkxoAoDUbhWN1j+PIGreBlnO8m+0"
    b"Zs1nZQ3Wn7pe2orv2fcQ19wRNQRRQxA1BFFDEDUEUfP7IJv12lbrXfEZJeKOqOk2SKtZvLSK"
    b"Z/brYXXZmT3lyRWle7utuexqCKKGIGoIooYgaroJ0s1PY3oik3VVzOyfQRDgF0I4AEuCXBYR"
    b"wmDyAAAAAElFTkSuQmCC"
)

icons8_align_left_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAAGYktHRAD/AP8A/6C9p5MAAACvSURB"
    b"VGhD7dnRCoMwDIXhbu//TsKcvpZrIBnDiuhAPa3/ByHUC+lBAi0m4HiTV5We3qtHEDVrQd65"
    b"Ym7OrD7Xbg/vxl5i4lmsr/C7r02YETUEUUMQNQRRQxA1BFFziyCj97MN3v8W94EqMSNqbhHE"
    b"7s4xN4r1yvWlemffavFuH0nDfK2k2BvDroYgagiihiBqCKKmmSDNHBrXvkjnXZX9GlxUnChr"
    b"wrCraSYIcIiUPoSrXBiRr7O2AAAAAElFTkSuQmCC"
)

icons8_circle_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"l0lEQVRoge2az0tVQRTHP6l5BU18Wgq1SOiXukjdFVhtQhGKWliE7toX4n/hDypJWmZ/gRkk"
    b"/SCCqEVIKBjlr2ihtagMNAnqKb0Wc6/de+687o9352nhFwbu9Z5z5nucMzNnzhvYxtbCjgRt"
    b"pYCTQAvQABwAqoFS+/t34BPwHngLvACeAcsJcogNC+gCHgLrQCZiWwceAJ22rbyjBOgBPoYg"
    b"G7Z9ALpt23lBO/AuQQdkmwfaTDpQAtwKIDEBDAAdwFHUvNlpt5T9tw5bZjLA1hAGwq0GeJWl"
    b"wxWgFzgSw24d0Gfb0NkeRy0YiaAWNdyykzTQD1Qk0EcKNUppTT9zNoecUIPeiTeoMEkajail"
    b"WedM7JEpQR9OI/zZG0ygFLir6XecmHNGN7FvA4UJkA1CITCs6f9mVEPtGiMj5McJB4XAqIZH"
    b"a1gDFjArlGeBXUkzDYFS/HNmnpCbZo9QTGNmYodFE7AmOF0NUrLwpx195jiGxjW8nBYJmPhd"
    b"QmGFZPaJXFEJfMPL7dLfFB4J4V7DBKNgAC+3sWyCKfypeJy0wxQa8HJbA8p1gueF4ESeCEbB"
    b"FF6OZ50PBS6hFqH01DyvyHgi3k84D25H6oTQS2N04kNyqnce3I4cFkKzxujEh+R0SCe0hDf+"
    b"Kg2TioPdeDl+0Qn9FELF+WIXARZejj+cDwXZNP41uB1ZFd82I0kMguS0wdntyFchtNcYnfjY"
    b"J96XnAe3I/NCaCvt6g4kpw3ObkemhdAxY3Ti47h4l5wBOId3RZg0TCoOXuPleEYnVIE/aZS7"
    b"/WZCJo1pXEmjO7SW8ecyl02ziwDJ5THqjKJFJ/6DVcoYtfCoQi21oQ9WFqoq7lYYMMsxFG7g"
    b"5bRAiMyjG38sNprjGIhm/MWHK2EULWBGKG6lctAcESqObUI5gypj5rNAVwTcExx+AaejGhrC"
    b"78ww+XGmCLij6X8wjjELVTiWxkaBsty5ZkUZ/pHIoE6HsY8W1aiYlEanURXApNGMf346c3RP"
    b"rsZr0TuzhqoAJnGSrEItsXJ1cpzYn0AfgBoZXZhlULtrPyqFiIoG1D4lNzt3OOU8EhIW6vcJ"
    b"XYdOm0KN0gXU3lOJiuti1H+9CbgIXMefAMrVaRDDx+1W9KGWVJshxhIbFxaqtL+YoAMLqB17"
    b"U25AFKOStzH0EzWorQH3bRs5hVGSl2rKgVOoMmY9cBA1UZ3UZhX4jLo1MQ08R12qkUWPbfwX"
    b"+A3NNtEphGbglwAAAABJRU5ErkJggg=="
)

icons8_flip_vertical = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"+klEQVRoge2aO0sDQRCAv0Sw8IEIIiIERBAsREEQRFLaWtra+APEytbS1tLW0tZSBEULRUEQ"
    b"EURLFUREIuIDTWKxGbwcm3CPvds9uA+uSMjNzgd3l5nZg5ycnKzTCSwDN8CB3VSi0QksAXdA"
    b"3XNkhm5gBbinWSAzIj0ogUf0As6L9AJrwAvtBZwVGQDWgVeCCTgnMogSqBBOwBmRErAJfBBN"
    b"wLrICErgk3gC1kRGgS3gJ0KyTohMANvAr2GB1ESmGgLVhAQSF5kDdoFawgKJiZQbAmkkn4hI"
    b"Gdi3IGBMZB44sSgQS6QILADnDghEEikCi8C1A4nHEjlwIOFQIsUW33+FNU+JI9sJ5MShAJxi"
    b"/17QHS0vLd09UkeVGy5SDnuC7vH7hOqtu4ymFpxIj19B/hDPPIGeUa1qn4HkwhBLxIu/RKkA"
    b"G0C/ieABMCYi+IvGN1QrO2RyEQ3GRQR/Gf+OEhpOYjESFBH8jdUXqlcvGV4ncRFhkuZW97vx"
    b"ecxQ/NREBP/woQrsAOMx46YuIvjHQVXUJTgdMZ41EWGE5gFdDSU0EzKOdRFBNzLdA2YDnu+M"
    b"iKAbYh+jKoh2OCci6LYV2gk5KyLoNnouUEVrwfM750UE3dbbJWpDtIMMiQjdwCrwwH/yV2RQ"
    b"RJDt6VsCTFGygPeFgUPLueTkZJY/7wYg/LWeLJAAAAAASUVORK5CYII="
)

icons8_mirror_horizontal = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"j0lEQVRoge2ZTYhNURzAf+Qj8pFEKESJEqUoSaIUZaEUK1asWIiFWIgSC7EQC7EQpShFiYWP"
    b"1TRDSlKTj5WSml7SJJPJMPO3OP/xnut+nHPuOfc9dX81Ne/e/zn393t3mundgZqampoSjAOe"
    b"Ad0txx4DPXruv2EPIPo1yujr3W0x8mAs0Et2yFud6Xh20ZROCxFgZxu8nBgDvKY4pJcOvyvb"
    b"MaKfyA8Rne1YXmAkD1Ic8hJzBzuOrRjBBjCZ4hABtlTsaEUXRu6IvrYJ6alS0IZNGLEvwFQ9"
    b"ZhMiwMbKLC14ipE63nLMNuRJRY6FrMUIfQVmtBy3DRFgfSWmBTzEyJxKHHcJeRBfM59VwAgw"
    b"AMxKnHMJEWBNbNk87qnE2ZRzriF3o5rmsBwYBgaBuSnnXUNGgJURfTO5rQIXMs67hghwK5Zs"
    b"Fsswd2MIWJAx4xMyjLnTlXFDL3w5Z8YnRIDrEXxTWQz8xNyNRTlzviG/gCXBrVO4qhe8VjDn"
    b"GyLAlbDK/zIf+IF515YWzJYJGQIWhhRPckkvdNNitkyIABeDWSeYA3zH/L5fYTFfNmQQmBfI"
    b"/S/O6wXuWM6XDRHgXAjxVmYC33Tz1ZZrQoQMALPL6zc5oxvfd1gTIkSA0yXd/zAd6NdN1zms"
    b"CxWS/JzjzUnd8JHjulAhApzwtlemYT6HC7DBcW3IkH7MT4Y3x3Sj7qLBFEKGCHDUqwDzbKqh"
    b"m2z2WB865DMwxcODw7rBc5/FhA8R4JCrxESaz2+3+XVECekDJrlIHNCFr/B/PhsjRID9tgLj"
    b"gQ+6aIdnRMyQj8AEG4F9uuAN5f6HEStEgL02Au8DXzRGyLukdNo73rCptaSr5Xufv0VZ9AXc"
    b"q6ampqYN/Ab7PEdZ7CnXLgAAAABJRU5ErkJggg=="
)

icons8_oval_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"TElEQVRoge3ZzW8VVRzG8Q+3yltLWxcI9YWYGDHGEIFYMNGFVTdojBr1L3ADSohB3BsCuFJ3"
    b"KqjhD0DRDejK+FaQutFECyTiQqoLSbA0JpbwUhdnGm/PzNw7vS9zr/F+k7OYM79zfs+9M+dl"
    b"nkOPHj16/JdY0qJ+bsdWbMI9uC2pW4bhJGYas5hKyiS+x7fJdcfYirdwGnNNltN4E1vKEt+P"
    b"l3C2BeLzyhm8iJXt+AFL8TIutPEHxOUCdiW561JkjDyED7C+RswV4V3/Tnjvf8Gv+EsYG4Sx"
    b"MoB1uBMbMYoHcEONvs/iBYwX0JpJHw7gmux/bBYf4VmsajRJ0vY5HMXlnFzXEi19i+18CJ/l"
    b"dHoJ+7C2CfF5jGB/kiMr93EMFu1sGKcyOrmOt7G6hcLzWI13kpyxjpPCH12TZfgmo/F5jLVF"
    b"cm0eTnLHer5WZxI4nNFoHGvap7Uua3EiQ9d7eQ2eyQj+XFg7Os0AvpDW91Qc2I/fo6AfLWJg"
    b"lcCQsK2p1vibaOF8NQr4W9gzdRv3CtN+tdZX5m/2ST+N10qXWJy90hNRBR6LbvypwPTWQYal"
    b"15lHKtgWBR5JAruVaXwY1W2rCPudao6Xo6cpjkXXo4SRX/2Y1pUsqhHusFDzFGGGqq5c3iFx"
    b"i2G5aJatdFZPw8S6r1dwMars5HakKLHGixWciyo3lySmGWKN5yqYiCofL0lMMzwRXU/AoxYO"
    b"nGndvSDeJL0gjhG2KPEUvLczGguxT84WBfZEN2eFDVq3sUH6u353dUC/9FOZ1F2v2LDgecUL"
    b"Ycr/ejoKmhM+ZgZKElqLVfhKWt+TeQ3ezwg+qT2OSVFGBM8s1vVurUZLhQ/7uNGUzpgPY7LN"
    b"hy8VcCCHhKeQZQcdxM1tkbyQNTgk2w4at4ixO4hPMzqZw4zg+o20UPg8t+D1JEdW7mMacDXr"
    b"WaaX8bFgdzZjUgzieXwi3zK9qo5lWsTEflAwse+uEXNV2CZM4Af8LLzbM0mZFzwoHADdhfuE"
    b"85BRtU3sM4KJfaKA1rrcKFj8ZR4r/IGdSe6WsxI7tOaUKq9MYrs2HfRkMYo3pE2zRspPSV/3"
    b"NyqmVYeht8o+DF3h34lgRvisPm/hYegpYXvUo0ePHv8j/gFzYrbzMmFdVAAAAABJRU5ErkJg"
    b"gg=="
)

icons8_place_marker_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"XElEQVRogcWaW2wWRRTHf1/hq4iNtJi0pSXBIhob610LmBoUiNJ6CYYoXtDok8YYwUuioklF"
    b"H3wg+OSLGhOjqFhNCSJq8BJFqtUnEZSId0wVKMYGsFR6WR/Omex2O7Pd3c4H/2Sz7ZyZ/5y5"
    b"7DlnznwF/KMBWApcDtQB9VreA/wJbAM2Ab+WoG8vWAh8CQSx55g+8fIvgCtPiKYO1ABbCBX8"
    b"FlgDzFVZQZ8aYB7wFLAzUv9doPq4ax3DecgWCYDdwI2I0mmwGNihbf8ALi6FgmlwAXBYFXke"
    b"KObgKAdeVI5DwPnetEuJGuB3VeBRD3yPKddvHOdtZr6JFzxympV5xyNnIhZqh9+Rbzu5UI58"
    b"ZwFwhUdeJ4yJvT6hThWwGugG9uvTjWyhyoR2Nyh3lxdNEzCb0MS60Ab8zVi/YZ6DQGtC+11a"
    b"7/SJq+vGKu1kjUPeBgxpndeAZmTLlCN+5Q2VDQFLHBxPa52V3rS2oFM7mWeRVRGuxL0JHPdp"
    b"nV5gmkV+mcrfnpCm4+Ar7cRmIlcTrsR42IDbdNeorDunjqmwF4mbyiwyYwTmpuCZj/ujLtM+"
    b"9ubUMRX2AQMOWS8wQjqTXK51DzjkA0iknBq2mU1CH3ASMMUiC/SdJtYydQKLbKr20ZdFsawD"
    b"OajvGRbZz4iCF6bguUjr/mSRmfNLbxbFsg5kt76bLDITWqxKwfNArE0U5+r7+wx6ZcZKZDs8"
    b"YZFVIisWICbWhftJNr/GjySZ8AmjWTv52CFvJXSIGxB/YxzifKCD0CFe7eDo0jolDeknIR/h"
    b"UeBkR50lyGy7QpRe3IM4FRhEYrO0B7TcMN59aUKdacAjyLl8nz5dWmbbTga3KvcrXjQdB7do"
    b"Z6+XgHuTcl9XAu4xqAD+RY65SbObFdWIIzS+KhOyml+AI8CbyIDuzNHehbuRAbwM/OeRNxFN"
    b"yBb4kXyTEUcRyaSMAGd54MuEz5DBtHngulm5Nnvgyoxl2vn7Hri2K9dVHrgyYzKSEhohXXzl"
    b"wgLCZEbJfYcL9xCmPfPiU+VY7kOhvCgiH3yAzGxWtBEmM3wYjQnBeOPPM7YrAF9r22t8K5UH"
    b"ZcA3ZLdgy7XN9lIolRetiFJ7sJ8e46gg9BstJdTLigLQCNwFPAtsRTId5kRn4qT2FFxrte56"
    b"/X8mkqHZCqzTPhrxaMUqgRXAW0iiIB6SDxHeazQA/UiIPyeBswnJkhxCruYALgGGLfwHtO/b"
    b"SE61OtEMvIoEcXHijcisLwNmxdq1a70PHLwFwojg4ZhslnK2ax/xiRtQnZrTDOAMJTGNh5HL"
    b"yweRpR4PUwjN8U0W+R0q20m6tFGj9r2N0SvWqbpasQQJoQMkwl2LJK2zYoF22gNMj5RXIye/"
    b"IdIl8eKYrTodUR37sOSPm5C9bUZbF6+QEc8pV0ekzKz0ugly1xOeUo8C50SFHxHeBfqwFBWE"
    b"l6S3I+cWE/ZP9cBfQHQNgA+jgn4tnG5plBctyDbq02cQexY/L05DdO6PFprZW+SxI5B7FPOB"
    b"PumZe7Hy/hItfFwL/8Gvp52MRMab9W9faEF0DZDrjFEdmpvaYeAl7PndE406RDdjirdgmaAi"
    b"8Axy8A8Q79sJXIvf29usKKoOnYS/aRlAdE3Uaw4SFgwS7u/DyOgfQjzrKaXSWrmbEc//HuGv"
    b"KwLVqQNLCJRkamuROGsFY/OwI4iB2IWY1B4km9iDhBaDyB4m8q6KvIuIg5yJXLXVA2ci/qyB"
    b"sYesHUiAuV77GYO0PqMW+aHAIuBS4GxKt92OAT8gh65PkIT5/vEa5XV+RST/1ISEDrWIcZiB"
    b"zPAkRq8AjF6hYVXur8hjVngPsqKZ8D/iZ4huqztQ5AAAAABJRU5ErkJggg=="
)

icons8_polygon_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"/0lEQVRogdXZT6gVZRjH8c+9edHECrWgugspCyJqJUirFv4Bb2FK0qJNLhRcikXoJhBdtYhA"
    b"JajlRTcuNHPhIoJAF+FKCgnh3sXtamVGKvgv/02L5xxmzumce+f80XnnBwOHeZ/3eX/fmTnv"
    b"zPu8DEfv4iIu4b0h5axEs8gax19Yj7FKHfWop3BIDlE8/sEk3sfiqgyW0TuYEabvNn7P4ADO"
    b"a4W6hW+xFcurMNtJS/G13OQ5rOoQ9xJ24gweFOLvN87txiuPwW9HfYDL8qu8G0+U6PccPsJJ"
    b"/Kv1bp3HXp0vxtA1ju8Kg/+AlX3mWiagjuOmVqhfcVA8orOYGMh1QSPYgWuNga5iW+P8MLRY"
    b"TAaTYnJonzB+G8Ygr+LHQtJjeGEYibtoTEzbVwpjXhwk4QJ8Kv4DGf7AlsE89qRNjTGb/5++"
    b"7v6bOCu/IkdVM10uwu8ND5vKdmp+XsyI90GGaax9BAZ70Z6Gl5/Kdih+XmT4Qhpv4qfF5JIp"
    b"eVGn5RBTj85XX9ovfH1fJnitHKTqx6ldz+KG8La6TIcmSIr6Ung7XiY4ZZBx3MFDvDFfcMog"
    b"8I3wNzlfYOogL+Oe+HKe84s5dRA4Ijx+NVdQHUBeF+uaO3ixW1AdQIhVZobPuwXUBWS18HlD"
    b"l2/AuoAQb/kMn3VqrBPIGuH1byxpb6wTCFG8yLCrvaFuIBvlK8iFxYa6gYzgF+H5klhToX4g"
    b"BEDT9+xoxWYGUbG2nBV/1OmOfKi1ZLSh2VAnkJW4Lvxub2+sC8iYKEY0Kzz/U11AmqvFaTzT"
    b"KaAOIBNilXgXb3ULSh1kXF5K/WSuwJRBRkX1P8Mp85RQUwbZK7z9iefnC04V5G2xTn+AdWU6"
    b"pAiyTL5Hua9sp9RARnBCeDottjpKKTWQj+Vb3Ct66ZgSyCr5hunmXjunArIEF4SXA/0kSAXk"
    b"sPDxM57sJ0EKINvlpZ7X+klQ3B9ZMzxfPY0/VfCwtd9ExSRVH1f6hRjVVoWoWLcH6TwhNkSn"
    b"VLP11ny0Wpasveo/T0QoE45QIQcAAAAASUVORK5CYII="
)

icons8_polyline_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"E0lEQVRogd2azW+MQRzHP1tV4qA9IF4S4Wma6EGCiwtOxEtLpE2chCxWRYtGw9FFwhEXf4Aj"
    b"J3rYNOEiIqFJaR3EQV1FSF+U7tq+OMzT9Jl55tl9dsx0uj7J5Nlndp/f7/vdZ+b37EwLtUc7"
    b"8BaYCo9tfuWY0Q7Ma9pJn6JMGERv5I1PUSb8Qm9kss6nKgNGE/o/ZSwmCYCDQD0wAHy2GBtg"
    b"K/ABWKv0zwPHbSXJAtMs3uo/QM5WcCCD+HKiw6kEvAKO2EoSIJuIJgos5chp4tv8ogDo0iRZ"
    b"aL+BfuAM0GgYfwswpsR9jrhLVukh2Ui0zSCGwjVgc8rYGSCvxJlAzBfrBIg5kcbMQpsFXgLX"
    b"ge1lYi/JkIqSBQqapGnbEHAL2BnGC4BuxLcf/dwADoaUSiswpyQ+AdxGlM20pkaBoqbf2ZDS"
    b"MaQkPx95rwW4CbxGDK1q79rVJXEQckdJ/iThc+sQlayf9EOyy6Vwlf3Eh8PKCtesQTyZHxGf"
    b"E9F2wY1kPfXEa/6BKq4PEA9S1cQ05aubEx4rIu5WeX0OuZxPA2dtCkxLFtnIO4MYzcBlhKlt"
    b"1pRVyUbkMjxH+ie5MS7WI1+B4ch5BjjsII+Eq4VVXjk/6iiPc9QyPE7lMrwsWQH8QDazz2VC"
    b"V0NrFnih9DkdXi43H/6bebKJeBlu9SUmAC4iVnUtBtePIM+TInDOmroI5RYpWeAhsDo8LwE3"
    b"EMvVJsS2TKPm2BQeG4E9xKtVCdhB8h6VVZJ2Rmy1btuCkyb7IRbvhAuKtgMmGXH58CoQL83/"
    b"TH1Cfx6xfaO+P4NYf0+EbbzM6zFgL3APaAivLwCXgC/WHFRgPfEtngJw2iBWM3AFTz/Je5FN"
    b"fETs+NUc75GN9PmVY8ZuZBMlxGKp5niAbOSpXzlmNADfkI10eFVkSAeyie/AKq+KDHmGbOS+"
    b"XzlmbCD+7NjlVZEhfcgmRvzKMaMTsY0TNdLrVZEBncT/rjEPnPIpyoRh9GuGQZ+iTJhCb2TS"
    b"p6hqqUP8INSR1L9saUN/R475FGVKG+JfhX6Gx5oz8RfUZnMRWR+s4AAAAABJRU5ErkJggg=="
)

icons8_rectangular_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"U0lEQVRoge2ZPU7DQBBGHwi3lAS65ATIiQInyQEQKOIGiANAzoAiwVkQFEAD3CBUEVSEFiQo"
    b"lmI8sdeEyPaA5klb7NojvW/9U8yC4ziO4/yelZy1BNgHdoBn4AyY1OiURwcYAi3gFjgH3mMF"
    b"CXANfIoxA9JKNeP0vh2k0xXBtZBDVWB5DKX4qgrSL9seQ+zKiQ7yUqPIskzlRH/sbeARWFfr"
    b"I+C+OqcoKXCs1mbANvAUK+ySfRdPq7BbkBFZpx//fGTRoBK1xRiQdZpDfyN/Fg9iDQ9iDQ9i"
    b"DQ9iDQ9iDQ9iDQ9iDQ9iDQ9ijbwg3ZJ5E5Q66XZQB3jAVjuoBxyptTdCO2hSVKTbLpbHiRTX"
    b"r9ZG4b7YY1NOdJC7GkWW5SZ2MSG07OUjfKXZY4WU+WOFS2BN3lR00LNH6HZPgTElPdYaaAMH"
    b"wBbhSVwAH00KOY7jOP+LL8rEkimh6HlnAAAAAElFTkSuQmCC"
)

icons8_type_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"m0lEQVRoge3ZTQ5AMBRF4cvqsP8VqH0wEBPx8yJt3XC+pDPhnURHTwKALxokJUlz5ZMk9TlD"
    b"3ojYzhgZsAmGzMHnSrmds60xRQ3RkKnoFNdSzpf1Wv/VN+5HFxkwekeeOLtXRb75uztijxA3"
    b"hLghxA0hbghxQ4gbQtwQ4oYQN4S4IcQNIW4IcUNIwNFOJeuuo5b9TiW86wCA71sAsWpmQWld"
    b"O0QAAAAASUVORK5CYII="
)

icons8_fantasy_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"70lEQVRogc3Za4hVVRQH8N/MpIVRoVZkDTUfggqLHn4ow6BQw0J6IPYCbUhTZ3ylidHLHtS3"
    b"oj5UUlAgRUlKlJEaFdHL6kNZJFlRaQ8ijfxQpviYuX3Y+3DO3HvPnfuc8Q+He+7ea++z/mev"
    b"vdba63BkYOZwK9AMHIu/MaaRSdqbo0tDmCmQuGa4FWkUH6KAt4ZbkXI4BUdVIXcm+gUiBzC6"
    b"3ge2yrRG4hvcqjKhbrRlxlw7yLzHYC5Oa1C/mvCS8KZ/wCx0FPW349co84LK5nUSHsAuvN0K"
    b"ZSvhfKnZFLAdN0ut4Eop0bE4qNS8zsaz2JeZ55Ih0L0EmzMKJNc2wVOtjf/vibIb4/9uXI43"
    b"0Vc0dtgcwuSowG4swM9Fih1GZ5Ttjm37M/378Xq878eEoVO9FF9EReZiRPzdGds2Z+RGC6ZV"
    b"wB+4T9gbj8e214ZM4xzcJN0jyf4YKazQ1UWyT2B27IdThf3Rh/Narukg6MCPApnB3Gsxnonj"
    b"Xmm2UrWiA1dgi6DQxzWM7ZKa2sVN16wKdAibfLXg97Ob+zuMw3S8j++xRrrhs3gyM25flLus"
    b"xbobIcSF5/CXUnf7IM6Nso8W9RewB5eWmfN6weUezshuxwqc3GwS47G1jHJbcWGR7COx7xDm"
    b"4Sy8Edv2CrlXOXRildTbJbnZOlylNGuoG+2YKmzKbBzYg6cEQg9JY8eNmbEdeDH2rcmZfxx6"
    b"8J6BL6sPH2FGs4hkMQaL8ZXSVTqMW8qMGR/7v860nYFlgoPIRvhDeBe9gnseEkzAT9K3NytH"
    b"7u4osyHTlqxSEuE3CNF/bIt0rYj7pSS6c2R6hPSjz0CvdEEce9AQp+3FuFdKYk6OTK9Aol8g"
    b"VHw+SvbEshbpOCgSU+kXvFM5LDSQxIlCUrkIR0eZ6XGeHao7cTYVy6UkFubIzJOSSGSWSffE"
    b"LtyFUfg2tg1pyWiFlMTiHJnF0gPX1kz7ttj2i5TQ7/gk3m9pjcqlSFaigE+Vrwcska7Ewfh7"
    b"uhDVC/hNMKEZgisudt8TW8oA8w10lQU8byCZLIkerI9yy6Vn9ocz8m1CipKNR6+2ksRtgmfq"
    b"x1JMwr8GkllaRIIQ3ZMguDfO0VVm/jZchy+FYFhOpmHMyZDoybRnyXymlAShVPqf9G1nT4vl"
    b"0CacZ2Y3Q/Es8kgkmCQ1szyZdVIiw1LIHowEwZwqkSAonxQnRubItAxzDU4iSTsquWFCnNiL"
    b"x5qpYDWolcQdVcy5Fuc0RbsqcbvaSCytct68w1SCTuWPwnUhuyfy0o4s0TwSx+GGGp+9Ssii"
    b"G0Y2L2p0JXrweQ3PbheOtzs1+OWgVhJLKsw1UaiiFOKYUVU8f5rUPU+rTuVSNIvEKLysNG/a"
    b"IRyeKiFJYwrxvmbMVxuJSi42Qa0r0iVUSvridUCN6UnWxVazsSuZUzF6hZQlD+2YIiSHSZVx"
    b"IzZJixfvCIG04kFrgdpWYlG1DCKOF4raxShXt+qLBC6K1yYDqyk745hOBnqCBULRmLASq3NI"
    b"PB3vlwg1q1rwjxAAW4bJaluJPJNrFO2Cd1ovNa1NUtM6EPumyXHHybfuFTkPGAoSxehSx2bf"
    b"LRA5oUxflkRvk5SsFjW73+T7xcqi9uEkQR0BcapU4ZXC97w7Db5vWo26UpQkfmSjbz0uttmo"
    b"K2mcjA/wp1AFn9JkpepBU9P4Ix7/A6+u1m3fs0SBAAAAAElFTkSuQmCC"
)


icons8_end_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"YElEQVRoge3ZPUvDUBiG4asqCCIiguAiFAQHwR8guDmKi+BfcHV0cHV1cHR1FFcHJ8HBwV1w"
    b"cRJxERFBEfFraIIZtLbmaJPDuaGEvsm5m4c0yckbEolEIpH4PzYx2OudCME7zjAX2Nnu8yfk"
    b"8jfsYDigsydBnrPlBRYCOTutByGXz+LU59HZxVhJZ6f1IBTlA1jDQ1a7xnJJZyf1IHwln8JR"
    b"Yd0exks629WD8J28gVXcZ+tvs+9lnD0JktPEYWG7A0z+0tnTIDkruMm2vdM6Oo0unZUIAhPY"
    b"L4w5xnQXzsoEyVnCVTbuEevo78BZuSAwqjUTyMefYOYHZyWD5CziMnM8YaONs9JBYATbeC34"
    b"ahkkZx7nbZy1CQJD2MJL2d/qC7VHdSP9tQpEcbLX/vIbxQ2x9lOUKCaNtZ/GN9X8wSqKR93a"
    b"Nx+iaAdF06CLpmUaRRM7itcK0bzoSSQSiUSiyAcoKiORfFCb+AAAAABJRU5ErkJggg=="
)

icons8_emergency_stop_button_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"CXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5QICAg0Rhg4xqwAABFlJREFUaN7tmW2IVFUY"
    b"x38zrumOua6lI5ooGvjCJCnmh/yU+MX6UuELkUNpKpZQCiGUb2Ul9smXD4WEHyKQzbREJSTI"
    b"ME2NXlhnYWFWymXXZdSo1hTUXXdn+/JceHg4d+bOvXd0hfnDZc7c85znnOec5+08F2qooYYa"
    b"HiQkYuaXBGYB84EZwHhgtPR1AwWgDTgHtAADg21DZgF7gWuyuCDPVWCPjL3vyADHgGIFAtin"
    b"CBwFZt4P1aoDtgMbgaGmrw/4BcgBl4Ab8r4BmArMBuYJD427wMfAB8Kj6hgHnHXsbDOwQhZc"
    b"DqOAlcAFB58zQLraQkwGLpqJLwHLxdDDOIcs0G54XpS5qoKxQN5MeBBIxcB7OPCF4f2HnH6s"
    b"GGrUqQhsitl9J4DNxnGcdthSJOwwu7WpBO1DwAvAPuA88Kc8PwOfAs+UUcMtZq7tcbrYXsX4"
    b"QImTSAKtAVxuO/BSiZM5qGh7gOlxCHLMGHZ9GfotFcSQI+LBPHgLTgEdiu6bOCK21tnlAcY8"
    b"DHTJIl8HngOeBdbKu14jzE8y5kUZ5+EVY5OZKILsNXEi6aMKzzvsxA8TgW+NMHmgX/IxraY5"
    b"RbM7SgKoc6eVDpp5YtADwNwK+e9yqFq3oVml+gphveSTikmvidhpYL/sokfzSYX8xwP/lBGk"
    b"UVIXrz9UgvmGYnBO5VjrZUK7m/8GcAQeZhtj9hMEcdte/9pS6uOHGardrBLCs8DnwH+GfrQY"
    b"bBBMBZqA4+IJiyVom33WFBiH1U687eg/r/r75Pf7kPaYEhtb6ujbqOY5FOZERqr2DUf/BNVe"
    b"BLwM3BavVCluAb/7LFSffEOpe0VYDDN3iSZ5qnkdHwhzIjfN/cHiL9WeEmGhCyRGrBEnYNHg"
    b"s6bAgnQZ47TIqfbCCIJkgQ3AZ8Bbjv7HVftyGEHyxl1anFDtJcCYEEKkgWXq/3cOmjk+awoV"
    b"EO861Csl6uXRHA6Qg1kcUOOvGbvzXLoOiE+ENbKrislrDpoNjrtDwieKnzDv3jdj1znGrY4j"
    b"RbFJ4wWHKg6RYoFe0LuGpl6qKj3iJR8DvjJjfhBeVu1bFM2uONP4rE9VxbvL3zQeLGEWfVxi"
    b"jRaiVeoBFq8qmv6oaTxSPNM3u3ofYX4E3jTvPyxzsToJPOrgNwLoVHRfxxGQZopaeEybfHS1"
    b"zqhetkQFsiA24Xe/0ad4B5gWV3S1O7s5wJingd8c9arFUv7xwzYz5r0404Q6Y9RFuZuX8yJJ"
    b"Sb3/lnG/lvGSW80pnnI4gchIO6qMXwYs0D0ipaDrPsKPcHiyfMggG7hk2mYm7JBCQZCS6Rwj"
    b"eFK8U6dDiEnVrv+OlQqgNeCc3LEbA/BolGDX4uBzKsxJRPmssBV4x1Ex6RMjz4m77lbpxhTJ"
    b"255y6H4PsBP4SOLGPcV0KZ5F+dDTL3FiGoMAGblTXKlAgIKkHZk4FhD3x9CEZKjz5bQmKpu5"
    b"LnecNilgtDIIP4bWUEMNNdwb/A9jBMuJwvmIngAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_group_objects_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"0ElEQVQ4jcWUIRLCMBBFHwwOzxmKJRo8shrNAdBYqvHV9dwhvrVgexNEN9MtkzZNp8CfyXRn"
    b"tvvz/24S+BIKoJSVRtSlqq4AWEliC+wkvgDHkYSJqkMTaljgEaFw35ewwE12HYtEaiyeVuWA"
    b"kVj3VC/fZkZqAb9l6PZUYx2SvAz9EIs+hUNw9mogm4PwLN/KR/gzyyf8A3hOJXypOKe1GcRf"
    b"plzTDOATg/Znu3oLSZS0NyMj7nG4SlwBxmf5AGwiFHbgCHU/7pEK3fEKHqlJeAOCaiebx3Kk"
    b"lAAAAABJRU5ErkJggg=="
)


icons8_group_objects_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"pElEQVRoge2ZQQ6AIAwE0fj/L+NJDx5A1NbNMnMj4dDJhjakpQCEsFzOdfB+NLfrWYMLScNG"
    b"ZBu834v6N6ZNRO2xn9gkYiPSohatx92sxyaR0cd+8CapkIZhkwgiaiCiBiJqPJ0jX9CaRcOz"
    b"xiYRRNRARA0bkaftN/vv3mX6RHqkf5FtEkFEDUTUsBGJar/pA9MmEXaIatiIsENUgx2iGjYi"
    b"AEHsbs4PYp2OHEMAAAAASUVORK5CYII="
)

icons8_ungroup_objects_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"rElEQVRoge2Z0Q6AIAgArfX/v2xPvTQrRSTEu7dWsOFJLEsJAGAmtpd7WRBTi3ruXRrojUMQ"
    b"87Sav7K0kZE9IiaMkRpyGtcXarnDGAlTiKTZrWgamhhRprvhMaJMad83WcKIAZelfLsuEsYI"
    b"hXiDQrxBId6Y4ThorTnCcZA3tI6DqvZx4Xk1ljCi8XYyyx3GSJhCehV7GZpxjIz61DUfmhj5"
    b"wPwfShgjAABzcQJJkRZZ1xWWJgAAAABJRU5ErkJggg=="
)

icons_centerize = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAd0lEQVRo3u3a0QmAMAwFwETc"
    b"f+U4gSBSbRsuA5QeSXn5aEZERZPqAKmjSzdAQEBA9qpzk6zJUZBHh80MbG8EBAQEZOlA/DI0"
    b"czXIm0uV0QIBAQEBAQGxNP6/O82EpNECAQEBEYgrht1ISBotEBAQEJCbfGjx8ewCQdYKbRHZ"
    b"jdYAAAAASUVORK5CYII="
)


icons_evenspace_horiz = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAeElEQVRo3u3aQQqAMAwEwI34"
    b"/y/rWVBREY0yey902BZSaHI8U67nrbXfS62o6yN7X+y5NqqrnWqrGSJJMvzlaIGAgICAgICA"
    b"NMz48HBXGrmhkXJHQEBAQEBAQEAMjV1z6gmgkYMpdwQEBAQEBAQEBKRNfvOpJtIsM9/aDGBS"
    b"7NmKAAAAAElFTkSuQmCC"
)

icons_evenspace_vert = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAAaElEQVRo3u3aMQrAIAwFUOP9"
    b"75zOUnCSqul7k5MkYPQPRhtlu0u8Fhc2MfTQWxFlGokqMwKFz1iuqN/1e5jsRgQA4PiMkrtr"
    b"EePFeDEeAPhvjM/F+0m/YrwYD59cv9vq96nGO2JG5vU/iNoMJLKY0+4AAAAASUVORK5CYII="
)

icons8_computer_support_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"iUlEQVRoge3ZT28NURjH8U9VQtJa2mixJ3RnodJYYYE0kbbBzkJCuhPSF9ClxCsQUQsLkSAk"
    b"pDQEb0DEjpWKSIgWCa2UxTmTGdN7zRVtZyaZXzLJnec55znPd87fmUujRo0aNWq0stqJ25jH"
    b"r4pd8zG3HZ1AzFUg4aJrrgjmdix4C1uKqEvQFn/m2FbJcKoiRKI+aa+0VdJ1VdeyPNeVlMiK"
    b"qwGpmhqQqqkBqZoakKqpriB3FJxA6nJEgV1/c1YFpBfjeIhZLOIDpnEe24sCVAFkDO+1fxf5"
    b"iN1FQcoGmcBSzOExRoVj+xXp0X1PJ4HKBBkTIBZwOmO/JOT0DUOdBisLpFc6nLIQk9H2HQfa"
    b"1B3AtryxLJBx6XBKNBFtixhuU28PPgkLwB8qC2Q6tjsa7zfiR7SdalNnSPpqPp13lgUya/m3"
    b"gploG2lR/qAwZ5J8P+QLlAXyPba7IWO7EG2Xc2WHM+WT1exHPmBZIG9iu/0Z2+5o+yrAjAjD"
    b"bDHaL8Xyv/A2H/BTdPStZtYtdC22eyJj68IrrTfFyVjmeLx/kA94IzruWDuYbtyM7d5t4R8Q"
    b"htmMMIQmMr6nsd4ZeG5tP3cuSfeKbmlvzGOwAHpj5vfZWO8deuBLTSCyOivMlSUcS4zJMnfu"
    b"HwL9r4og9uEeTmKrsJr1C3PimfShXMhWOhwdCwLM5lVLP6gTiKJR8k6mJ7KaLKi4VsMpC3ET"
    b"U3gt7BuzuC9M7J6/PanDeNTB01hNiOTIMRXLV07duCrd4Pbn/HulENexfk2z61DrhCdc654g"
    b"PTPVGgJeCokeydlrBUH652pvxlY7CNLz0EVswlE1hIBD+Gn50nxVjSASDeIJPuOFsLd0rWQD"
    b"vwGZX5eIvM3txQAAAABJRU5ErkJggg=="
)

# ----------------------------------------------------------------------
icons8_smartphone_ram_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"5UlEQVRoge2YQQ7CIBBFX3tDvYj0jMZLVL1K6wIaF1ogJoUB/0smDWEW88N8SAeEECKwhrC6"
    b"D8CYSmiFboR0ywhMwIN3b1qLO+CAISZkMlBobriYkO0kTrGkypzxNc6xpCUkRY+tMgO+xiWW"
    b"lHVnG+Cjzpzr9wZcDa2/kiNkazcr6yy6bq0m+MUjpTnMI6WRR5pEHimIPNIk8khB5JEmkUcK"
    b"Io80if7ZK66z6MYj26b1AR0khDzD1+rIdMCPTMGPd3dx1B9O58YlpdjhB8S1C92LOYiw3P7H"
    b"krrJau8Df/ayCyGEHV4Hpj6QuXY7DQAAAABJRU5ErkJggg=="
)

icons8_image_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"lklEQVRoge2YP0oDQRSHv2ghiFqZwl5whWgluYAgnsXGzhS5g72HUJEk4BFSiYJXMGJKBQMW"
    b"iUVmyBB23Jnd2cyA74MfYZd9w3w7b/9kQRCEf0EDmMWeRAjWYk8gFCKSGiKSGiKSGiJSE32g"
    b"DWyp34FP8SyR9Czzu3esjy6gc2IRabvUp/SutQN85ezfBj6Lin2ukTHw4nG8LweW/YeuA7gs"
    b"+xg4AjLg27HGN33L/AaO9YUHfAAtY+CrmkS0zPJdy7XWWWIfWFcZ1ihTNoXtBPOWelerobfr"
    b"arGgIuZKtNT2DJiwuPg6ltqfVERsEjpDFi3WA+6ALnAONC01KxfJa6e8og5/kwGjWCJFK2FG"
    b"t1hTrUQXuAWePcaoRcRHwpTJ219mrCAiru3kE3NMGxnwFFKkrrO3/CDNYwO4BqYhRPTZCbES"
    b"rpkAl8w/EAKcAm9VRVYtYeYR2FMyu8BDFZEY93wzI+BMyTSAC8q9NUSV0JkCN8AmFYgtYeYV"
    b"OC4jkdI/xEqk9hWlNCKSGiKSGiKSGiIiCIIQhV9aqvtgADl99gAAAABJRU5ErkJggg=="
)

icons8_cursor_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"CElEQVRoge3ZT8hUVRzG8c+bovYS0cI0IsgMw4VRFEJERIskUVpFhKvMpKRFi8CEFkok9HcT"
    b"FES1aOGmIhe2UHFhRNRCJCIysDAI1LKgIq0UdVqc3+VeX+Z9Z+bMvXPnhfnCZeY899zD88zM"
    b"e87vnJcJEyZM6MFRfI0b2jYyLJ24fsCKlr0MRadyncLt7drJpwhxIF5/w9pWHWVSBFmED+P9"
    b"Waxr01QORRBYgHej/R8eactUDtUgMIXXQruILW2YymFmkIIdoV/GcyN1lMlsQWAbLsX9V0bm"
    b"KJO5gsAmXIg+b+GqUZjKoVcQ2Ih/ot8eLGzaVA79BIH78Vf03YermzSVQ79B4G6cif6HcW1T"
    b"pnIYJAisxs/xzBEsbcJUDoMGgZtxPJ47hpvqNpVDThBYLpX/HfyEVXWayiE3CFyHL+L5X3BH"
    b"XaZyGCYITGN/jPEH7q3DVA7DBiFVzh8pK+eHhjWVQx1BSJXzezHWeTxaw5gDUVcQUuX8urJy"
    b"3lrTuH1RZ5CCauW8veaxZ6WuINO4BffgYXxeGXtnv4NMDWGgCNHvGLdJ+5Mbcb20niyXgszG"
    b"3/osZ0ZZjW7G013089LBxa9x/R7t09Ja0zi9flpP4lNlTXWn9Nu/iA3SNzQWxeNcQXZU7u+u"
    b"6AdDe75Za4PRLcgUXg292OqewZK4/2BoJ6XFcCzodorypisXtiPRrp6oHA3tidHY7M3Mc60P"
    b"on0O60N/PLRvlbPbptC+Nyb7+CLIYuyN93/ivkqfxdLs08EDoS3Aj6FtHJXZuSiCHFb+LdzV"
    b"pd+LcX9vRXs2tM8a9tgXM0/j18zSb5l0jHoJK0ObltaKjrSit0oR4gRu7dF3T/R9o6K9FNrH"
    b"jbgbgEP4Sn//sVqr3EBdE9oy/CstkL0+iLHiSynMMxXtndDebsVRJo9Jpo8rp92V0jdyTiok"
    b"5wULleda6yv6J6HtasNULi9IpvdHexFeVk7fY3k23I2l0qH2ZakmO6mc/b4zj4LA+65cg77B"
    b"U1IVMK9YLS2Gh6Tjn2F2qRMmNM3/zsPl3mj86SEAAAAASUVORK5CYII="
)

icons8_pencil_drawing_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"f0lEQVRoge3aP2gUQRTH8U+CSY50Aa20sBVMjKaTdCrYiFZa+ae20i6FRXoVES0iWoiIlWIU"
    b"jVpo5R9UUAwWighRhKAmSkALIeEsZo5L4t3lcu7eJsf+4Li92Xdv3vdm38yb3SNXrmrqxUec"
    b"auTLa5KNpWH14iHWoTvjWBrWJkyiiDF0ZRtOY2oJiD58l0Nkr5aEKGQbTmPaosUg7skhstN8"
    b"iDuSS+xOXMJ1tCXks6rShLgd/X5Be0J+Kyqty6kTo9HvN6FGS005RA21DMQtOUT96leGuC89"
    b"iL6E/FZUP6akC/EDAwn5ragcooZyiOWq5SAeWKUQ2zAdO3stOYgu3I1+p4T1KDWtVR6JIn6j"
    b"JwG/iyH6E/BZU8djZ4/xPB7v/U+fTYeA8djhPozE43M4K2xsRrBjGf66hD17UyEGlEuEDuH+"
    b"bLHK62Qd/jKBgPOx0zPxcynh3+AEDmAIv2J7rZEpyAiiSznw0myyU8iPxfvkoWg3UsVXZhCw"
    b"P3b8ahm2oxXOFYTSvgSxNakA56vWxv1IfL9ch58N8X1yUXsBN7FbWOx2CetQ07Qes/gjrCNL"
    b"6anwix8ToNosHIlpKY3EUipd8zfqsB307wz2CS9lDNGGdzGIPXXY9wn3l54J68pbZaBpobzJ"
    b"RNtjEJOW94yxQ5jRnlgBEHAxBnK1TvvNOI2vyiMxJWOIbszEYOZwuIpdD47ihYW5MS7UZvVM"
    b"EKnqoIWBzeFQPNcuJPYFoQIu2fyMbYPNDraWKtVSs8Kd78+L2saEhXDFPTrbKIxAtaKwiPcY"
    b"jrYrVsMqBz+DK0KdlfqziCT0wcLceCTkzKr4S8X8dWJCgLgm1FcTmUSUq0X0F8OGEKWXtluf"
    b"AAAAAElFTkSuQmCC"
)

# ----------------------------------------------------------------------
icons8_light_automation_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"oElEQVRogc2af2iWVRTHP++23OrdkoLSXFsoo9FoC40CyWFulGWLLUiWEkQa+yPKgn6Q/wlJ"
    b"aoQQBEX4RwX9oYsosR8EpVikC3JulT/ISjfLpbasWU1x79Mf5zzeu2fPj/u8e9+3vnB5n+ee"
    b"85x7znPvPfec87wZkpEBFgCdQCtwDXCt0oaBEWA38D6wz0FeyZEBuoHDgOfYDgPL9dn/BRqA"
    b"rzAKHgVeBu4EGoGstkZgqdKOWvx7gXkl1zqAVuAkotAw0AOUOzxXhszGj/rsb0BbkXRMRBtw"
    b"XhXZBlyWh4ws8I7KOA/cXjDtHNGAvEUPeJHprfMM8JLKOk0Jl1kGsye2UZjNmsHMzJ4CyUxE"
    b"tw54jPyWUxSywJDKvr+AckORwbjYh4og/2GVfZAiz8rNGBdbVgT55chMe8D8IsgHRPEuvX4P"
    b"yBVhjAlgu153FkE+IIYs0uuPInj2AYPA7Bg5s4EBoC+C/qH+tqZVMA38/XF9BH0As8bDjJmt"
    b"NA/oj5DRqPRD09I0AWM6SHUE/WrgW0wsNceizbJohwI0G9XKM1YAfSNxTgepieEJM8bVCICZ"
    b"yvdPAfSNxIgOckMCn72EDgau4/YPQJPy/jwtTROwWwe524HXNsbVCIAO5d+Zp46JKEMMATdD"
    b"RoAl1v0S7UtCh/7uclctPRZgQnbXA9GfERdUYJZvc2rtUiADHNGBuh2fSWPIKuX9Lr1q6bEa"
    b"430qHPhdDanChCcr8tYuBSqA73XA5xz4XQ3ZqHwDFCeOC8VSJNYaB25M4HUxZCFwQdvCaWuX"
    b"Eq9j1nM2hi/JkCuAnzDZZslRjRjhAW/F8MUZkkEiaQ/JOmckjJkBepGZC5aX/kKKH3mhCTir"
    b"glZH8MQZ8oTSRoG5juPF1cqOuSoehgcwb+S6EHqUIfX6TA64z3GsZSpre6C/ApmlCdw8aSS2"
    b"6gBvhNCiDHlb+9+MkLkIeBAJIn3458yWEP4TSqu1+uYBjwItMbpPgp9DjIbQogz5XfsbQmgr"
    b"ref+ADYDjyARhQesD3nma6X1IefQu8gM+SlBvasxUQqn7a9GIl8PyThzFu8EUgAPC1+WA8eZ"
    b"vGf+Bg7o9dZSG7JB+79AvFQLsmSHSC6rVgObkGW2DrgKyX38hHBxkhFxiqXhb0AO2QmkYmPD"
    b"P+2rEG/Xh3jMs0ghfA1QGeD1sVbH2o9DbTrOLcY1G71Eb2aAOqS4ESVrP+Z7jI1KTLDbU4r4"
    b"x186p5j6VquAD5D9MYjkLTXaOoBvgJuAHZiZ8ZFF9g841MsKsbSewniaz5jsSp/EBJVhxY8a"
    b"4Afledzqb8c4gVHglnwUy4f/DuAXpdlZol84vydGZpfy7NX7uZgXsxNZmnkrlg9/HSZa8JFU"
    b"igKZFQ/4U++zej+OtVRLliMg58g5pNofF1kHEVf4vhi6JBlyUn9vcxjQL73+GkKrAz5FNmwO"
    b"qZOBHGwQ/1WrXX/9VHkWMiOVSGXTRbeLGV6atjEg41ZkQ3rIBm23aGu0f5DwAuHlmG+Sj1n9"
    b"bZiMdgJ4JsmQcuB54IyDAWeQEzwYqb6K2eRXBmiVyDnhId6pE+N+uywj+pma11wKvKL000mG"
    b"+LgXs8GeRlxoLfAssu5zRIcKPfrsEaaeBSCHnW9MWOtnssu28Zry9LoaAvBCxEA54qe23FJ0"
    b"bYDm79FK5JzYg3iyMeBLZDnNCPD6mI/kK+OER9uxWAZ8gkzlKeBj3L6lL8aE3nOQwG8dEghu"
    b"It79guyrISTQbEE82ecqc0NaI6YLP1E7gITi9qweR0L2IJqRzNEO+3NIKuAhLj3pJRQc9ZgD"
    b"cAJJklYgEa+HJFFBrFfaMJKEbUaSMt+olUXXOgLNSJpq/4GgFlHqRAj/FqWtsvpmIumy0/lR"
    b"SthFhksCtB2IIXeVWql84deHo1rTf6daOvRgaml2u4DjX0r+BXGoAPepC/FyAAAAAElFTkSu"
    b"QmCC"
)

# ----------------------------------------------------------------------
icons8_light_off_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"AklEQVRoge2YvWsUQRiHn7vEC+qBIJfjEL/SJCgKEsHCaNRKLVTQiDYWIljaKQp+RFTURuGI"
    b"xMbGziKIf4CKhqCNIvgVsRBzEWIiAbkqCXgW8y6ry87t7O3M5Yp9YFnY993f+5vdnXnnDlJS"
    b"UlJSUlLIONDsBQ4B/UAJWCPXK8AU8BJ4Arx1UDsxGWAAGAdqhsc4cAQ3D7MhuoBX+Aa/A2Vg"
    b"L9ADLJejR66VgYl/8seA9U13HaAP+IkyVAFOA20G92WBo8A3ufcXsMeRx0j6gTkxMoJ66nHJ"
    b"A49FY040m0oXMCMG7pDsO88Cd0VrWrSbQgZ/ToyIkaRk8d/MGE1aAAak4ASNfU468sCkaB+2"
    b"qBtKBn+JPRkSLwIX5KyjEzgDFEJip0T7UzKb0fTiL7Fhq9N5iX9GNcMgJYnVgLMh8TbU6lcD"
    b"tljwq+WqFClr4kV8o8HBlAKxTo3GkORcseBXy3Mpsq9OTtBwSXNNx37Je2rBr5YvUqQ7Ii9o"
    b"3HQQoHYA3hbGGVUpkjfILQIf+H9vtcrgvrzkV+MYi9sDcnKeN8gN9gLT3rAg5yWG+Q0xjXpa"
    b"9ZZXSPZplSR3KpHTCLyOviPCSJLJvhO/wzvjnhS5rInHWX51b/WS5AxZ8KvloBT5qImfI1lD"
    b"BHgv8QOJnEbQgT9PtoXECyiD9eZQUXLCtihbRXtGajnlohQbxf4u1Wu4Tru6x1LUXqsGnLCo"
    b"exz/l+Yyi7p18bbyVWCjBb1u4LdoHrOgF4th/I69MoHOCvwdwAMLvmLTAbwWAy9obHLmgGei"
    b"8Qb12S4KBeCrGHlEvC1PBngo904Cq627i8kGYBZlaDDGfYNyzyx25pkVdqE2e/PAJoP8zZK/"
    b"AOx26KshbqOe8LBB7n3JveXUUYOsw/x/X+9Ya6u47c5cW6z67baEAkQZjDvgSGz8S9gSuBrI"
    b"qGi/I3xuWMfVQDyzfxzpO+cHahDb6+T04XfzluUm5kvvjUXyaEQONRjvzYQdk6hB5DQaLUc7"
    b"cB31Q6kCXMPdcp/ScvwFg4D0wSiNpC4AAAAASUVORK5CYII="
)

# ----------------------------------------------------------------------
icons8_light_on_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"P0lEQVRoge2aT0hUQRzHP09Fq02CYNmlDkJYUuShJLwkhVHdrIOhp6JLl07dO1h5MezQyS4d"
    b"K5ACCdJbEgXZv9X+oR5aTMmif5R1sj/bYX6PN26+3Te7My8TPzCMvPf7fX+/mXnz3syssEJk"
    b"7gCP/nUSNshJcUqF6wBxsdKQpUZVDDHuEcMcicop4CaQjDFmErgBnLQpOoDq1edAyqZwCCmJ"
    b"lQOu2xROasIvgXSInQc0AWeBYWAC+C5lXK6dAXYWiJWWGH7HWX8KUlqAsbx7HtABTBJ8N4qV"
    b"SeCI+Oo8JegwZ6OfRjViRLtWDzzUEpwCLgIHgAYgIaUBOCj3pjT7EWCTpvcAGCV81J3QAryX"
    b"hGaAE0BlBL8K1GhkxfcT0Ooox6K0AvOSSD+wpgSNBGoy50Rrr7XsIlKP6sUccJ6/n3MTPKBX"
    b"tD6y8DFzikcwJ/oprxG6pj8y9y1pFqVDAr6mtMcpjAQwLdrtFnUXxSN4xR5zoH9ctMdxPCpN"
    b"BK9YFwvOStRI54AdJo6myRyWegD4begbhV+oNR3AIRNH04bslnrI0M+EQalbTJxMG7JR6leG"
    b"fiZk82IZs5aFSwe/3NVs5uRabalBIlArMeYM8oo0IvqmqFrq+XIyLYKvXV3QqszNmr+ucrkn"
    b"SUuMdyZOpnPEnxubDf1M8LWzBa3yMG1IRup9hn4m+AvHUYcxaCPY9LjC34m2OYxBDcE8aXag"
    b"768cPkgsp5wmeP3ZXg8Ni3aXZd1FWU2wHjpqUbeTYKeZsKhbkHYJ+g3YZkFvC/BVNDst6BnR"
    b"J4EngPVl6KwDXojWZQt5GVODOgHJoX4DKWVyVgO3ReMJ6rGNhTTwGLUdBfWF909CrmE2+T3g"
    b"ivhOAxvkegZ4hsPjIP2ALkOQ9FbgM+Zvmy7x+QI0atfHcHhAV+zIdA/wA7Xg2x5Br1HsfwL7"
    b"8+45PTId0oTDeqlHbPoi6F0S296Q+/oh9mCITUl0A7co3Dt1RD/39UtdAb2kxDwXJUHbX2bT"
    b"PYK1+Mvmp7dl0xDb6L+pN8vfu4rYWcHliHh59X/FW6K/sd7YDGx7RK46so2dVcAFYJbwkZhF"
    b"fQid7wBtUYX6kM5I6Saef1BYYUnwB/Bb9Q/vjd5CAAAAAElFTkSuQmCC"
)

icon_cag_union_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAHzAAAB8wHhR67u"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABHRJREFUaIHF2muI1FUY"
    b"x/HPzrqabpqSlrds1cjAKDaTrSiiIMWsXhVZRFYvKqgMKqQLhCXUKkkSalFBN6jEjKJeBFJQ"
    b"2T260GUrs5tvDOlmmqtu2otnZl23mdn//ufM+IVhhpn/+Z3n/P/POed5njNNGssJWFh8n4zj"
    b"cAT24Vd8V3y9hRewO6twU2pLy9CMBViOiegWRm7GDvyBw8Rgjse84vu/eBTL8EsD7KzK1egS"
    b"d/ZpnIlChnZjsRTfFts+hNY62ViVFryG/ViLKTl1CuJm7MJfOC2JdRkZjQ/FnbwikeY48WS7"
    b"MTeRZlVGYCM2oS2xdgGrxA2ak1j7IJqFT2/D1Dr28zD24JR6dbBarDTt9eqgSLN44r9heGrx"
    b"NjEhO1MLV2Ai/sG9qYXX4WMMSS1chRuwE0enEpyGHlyQSjAjLdgiXDoJ67Bd+G6jWS2W5CR9"
    b"78BjKYRyMEVsuufXKjSuKHR2rUI1sBn3ZYl7qjFbDOTT2u3JzQY5lvwjcSdexldiye3G9yLI"
    b"K3E6xtRuYyZuw49ZLz4Jz4tQuwcf4C6xyz4u0oG+0Wkpcr0nkbHVuBl7B7polAi/94oYaqHI"
    b"HUpci8UV2jaJOVT6PD2vpQNwlbjBFZknXGenSIzKMQMzM3Q2AV9iUXb7MrNIeElZ5gvff0+k"
    b"oikYKVxxfCK9EivEFvA/LhautFK2bO6QZG59eARv9v+yQzym5RlFCiISHewyPlu6gK8LS/p+"
    b"0SrSyW8Mbst/qWjYYBiCt9W+I08V+9hB/XfidwdWmqycJZbnwdIm3LgWVoi53OsR4/A3rqtR"
    b"uJEME5P8xb5fPiNC4qE5RZtwYs62s+TL9G4UUXevBxVEDrwspyHE/OrCsTnarlR5n6rEeGzV"
    b"b8GYKyZMWw4j+jIfr+Ro16GfewxAQdy0n0XVppelYqVKwegcbZoNbrFYK4ocs/r/8LooSaZk"
    b"pvR15VJday+uL3fBVtySuNNV4s6NzHj9JNWX/TF4VaysFYtzPaIikZpFuDTjtUuUL682FXV2"
    b"iUGcWk1knwjP60k7zlHZ3RaLlKDECFwm8p4e8TSqxnQFMdqq8XwibsLXDuxVo4TLNIsDn3Y8"
    b"KBKy7XhSLEIni1LTzoE6+EFkWY3g8D6frxRFvU3C8G5xWvWuSF8HvQJuwBO125ib0cIjLqxV"
    b"aK2ooB8qzhUDGVur0EViZ59Uq1BO1kh0RjgEf+L2FGI5+t6BZ1MJ3o+fRGG4kSwQbpUn2CzL"
    b"BLEM351KMAMt+EwUwZPylAjnJ6YWrsAdIrWenFp4uEh1P1f/I4IOEcHeWq8O2kVMs6ZeHYh/"
    b"NewSteNai+hVmSOOgNfXoaPp4hjgC3U4yCzHJeLRd+GoRJrXiDmxUbrqZSY6xJzZVjQi77yZ"
    b"Jv7tsx/PaeyBaS+tYo/ZLf6G1ClbKNGMM8SR3J5i28vrZCOyp6PHiBrrHGHkR3hfRATbiu+j"
    b"xFHxeSKfHopPxODXq1+q0CLHXB4motQVeEOEFz3F1xYxuHfwgHCpejNJbKgz/gM/suiaaJQA"
    b"JgAAAABJRU5ErkJggg=="
)

icon_cag_subtract_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAHzAAAB8wHhR67u"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABAlJREFUaIHd2luIVVUc"
    b"x/HPmZlKzckGNMuBYlQoTNIw04qmq1j5IFQiRRBFD90ZzKKiol6GLk6BlVIZ9BBCUFEkWhRB"
    b"lF0pqYfCbhZ2o6ws7WLWTA//M3mc5pyzz95rzlBfGJizZu/f+u+z1/rf1pQ0ly4swtG4Dt+X"
    b"x2eiBy34E33Y3GTbMtONXhyL1hrXjcH+FZ9LI2lUM5mHh3DIaBlwBc5NpNWJR3FGIr1MlLAC"
    b"FyTWbcGpiTVrsgBnNXPC/zoHjrYBqViLialFWzR5I2IqVlYakIJz0JFIKyufYgcOTym6Vu0g"
    b"N1KMG5y3LYHYVLyHvxJoNcqvozDnyPJ/yGNKWFhkaR2Mw3AQnkliUj4GsKSRB2kVEfsynIAD"
    b"yuM/YwKW48iy8Du4L5mp9RnIclELLsEW9Is6oRcn4kF8N8w9nYkMzMoD9S44ChuxC3eLpVTJ"
    b"KmzNMFEfzm7UugborRUQe7AJuzEby/D5kGu2i0KoHstFOrHa3kVTKqqmKivEuutV27NdJKJr"
    b"Vu83U8Sd1Dw83OBNIrhdnkFgvnjgQxMalYfVQwcWiIe4OKPAGPyG83NMPla6XG+vFdGJb1V5"
    b"TTV4EU/mmPxkXJ/jvro8hQ/FN9UIV+EPe+JKI6zEtBz3VWW6iBF5lkg7fsdtOe6dKEMMqMFc"
    b"EYT/4Vl8If+avV9konlqkiJV3loV7rxdxIpLCwiOx1dYU0CjUZbiwsqBJSJyTygovEgsz6UF"
    b"dbKyzBBvdS9eSSR+h1hi3Q3eN1uCUvll3FNUpEwLNggv1kgz4jycXnTybcKFpqIN60RgvVW2"
    b"9GWOKA9qMUMkrlXZLZ/brUUJt5S1N+KYOtd34YYqf2sT+2GVcCpV6RftnJFghoj8A3hOOJbh"
    b"suXJuKaKxjSROtWkTXxr7bnMrM/7ovF8Cm7GY2LJbcZL+AA7MUUc/szBLJFhDDqgT8o/ddmi"
    b"+mtNzSRRbW7AG6K++UF8mV+Lo4iTsF8e8XV4JIWVBdgq9kBuWvCmaCaMFuPFadTTRYWOF5sx"
    b"aQ+1ARaLA9DCnfWSqL2b2b6pZL0Eb2OQPpFajEslmJEu4f7PTCXYIRLH21MJZuR50RdLVfIi"
    b"/PwvoshqBovF3lyYWngfvI63ZOtVFWGK6A+sH6kJusSrfsLIHdx0iPOUdxWvgWpynEjDX5Az"
    b"wtZgEl4VKUdT/pOhWzQUPvLvfm8Rze0iiiftnAxl7pAJpotcaIfo3eZ9O5NFr6xfpPR52kYN"
    b"MUsUQjdWjO1b/rwTXwrPlqU9WhI1SJ/whNtwdUJbh52wGmNxLe4SaX4Priz//o1Is18T3meX"
    b"OLnqEkcR88vXfSzK6DVi340a8/C4PZVZK04TS+VtfIafRBr+o3jATbgTRzTT0L8BzGe6xLiL"
    b"7tsAAAAASUVORK5CYII="
)

icon_cag_common_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAHzAAAB8wHhR67u"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAA3BJREFUaIHV2luopWMc"
    b"x/HPXttsRtu2t7bDjjBrmDFm2pHaacpEkmHQNqGYFEPulDQolMNcuJDD5BSGCxkuKE1N5Nhc"
    b"SE0aUhSJMkoOaUqOMwYX/zXTsqy93tPzrr18a13s533/v///eZ/3eZ7/89/vsP6yFKvwaevv"
    b"O7EeR2Fnq+1+jGEX9vY5vlxcibtwWsZ947gUM7VHVIBVmK6ocS42YaJ6OOW4HXfj4ARay3BL"
    b"Ap1STNakO1ST7r9YgDNr9rEea2v2YRNW1uxjCI9jRV0OjsG1dYl3MILhPvnqC8k7U9swZ7AR"
    b"x6cSG8WzqcQKcoLIBJKwDuenEivB6amEDjIAE68vm0vNDGGm6pOcxho0xFzZiz0VNctwb1GD"
    b"IZG93iw2vjfxd8fvJ7wl9pSxVJFm8EyRmyfxIjaIzizADhF0E8uxWiyJ2/Fr6/cETkwU8Fwc"
    b"XlVgu0hLujGGG/A5/sTD0mTC3bis18UmbsoQeBVPZdwzjDvE3PlSPaPz9FwXVmKL7MPMVryb"
    b"09lifIXvVD9sdfJgt8ZjsVnMgTwCPxRwOIo3WjZLC9iVJu/+ciH+UuwQtVCM4hfifD4QHIY/"
    b"cFVBu0nsxtsJYpgVOdcBTioptBXbStitFvvOxSX97ud5bSnSkXrM/Axmxeu1pITtO/hG+VTp"
    b"EFzX3nAPTi0p1hAr0eslbE/BPtVHBTEsz1XUWCtG5ewStq/hlRJ2TXHkPUADUyWEOnlJ7BNH"
    b"FLS7WiwYowVsxvGyjo6kYgLf4mPFUpGjxWheUMBmg/KLUy6W43eRTB5awO5HCY6si6sKdHAG"
    b"vsf7WJTTZqfY8XsxISP325zTWRGaIrhfcKvso/A2fNjj+sliTvR86HV0hJgnj4kU/mux3s81"
    b"obfgky7tC9u0MnO/ujqyn2bLx29ihHaItP48sYlOidfqgzabK/ACrini6KLqseZiHDfiPfzs"
    b"v0fkXW33TvkfFUbGxSo3g0fUX8XvC0sMQG1sYGjg0fkOoioNkR7swXHzFMOylGKL8EBKwZxM"
    b"iyNEUmZTC2YwJAp+lYtr8806XD7fQaSg9uV2ArfV7SQ1jS5tu0WS95D4J05KzhEFwL5ylnQr"
    b"2Yj4oGaj9A+nrzwpPrAZCEbEFwdr9C4UpCpmFKLIyrFP1GxX4HrxinzWdv0+URG5pKX7UaIY"
    b"c/EPAZKIlZ2aclcAAAAASUVORK5CYII="
)

icon_cag_xor_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAAHzAAAB8wHhR67u"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABMpJREFUaIHF2nmoVVUU"
    b"x/HPe0+zEbMyNZyygUqxScOKrKw0oiIjgooiqH/CimzwD0mbw0yEgtRACiJIqGiAaJ7IAm3O"
    b"Jk2bJ23UrMyh+uP3lKe9e9+59577+sL5556z195n733W+q21b4vuZW+cghMxEAPQFxuwGsvw"
    b"Dl7As1hX1HBL2SPthFacgykYiR9lkJ9gVfsF/bAfjsAorMX9mIUvumGcVTkVH+IvzMMYebGu"
    b"2A2T8DHWYyZ2atIYq9ITs7EJ8zG4TjutuBArsRQHlzG4ouyK1/ALzijJ5h54UrbbhJJsVmVH"
    b"LMRy+bDLpBVzZJuOL9n2VrTJrH2DYU3sZy7WYHizOpiM3zGiWR2004bn8D62L9v4UNm/15Rt"
    b"uAID8DOuL9vwQ3gLPco2XIVJ+AP9yzI4UCLzaWUZLEhPCZQzyjJ4Az6XvdvdTMF3ZfW9AtPK"
    b"MFQHA/E3jm/UUJ92Q0c3aqgBluCmIrqnGofgH9mr2zU8pPp4FaNr9TK743Qch8MxRCLuV+33"
    b"f8ZHIlGexkuit5rJMpxUdEVG4gH5sO4UdboAiyV/GCsaaEr7b+PwjKzUVPQuc+TbsFK0WFV2"
    b"ERW7QWb5bOzQ4f49eKRC28G4Dj+0XxdpTv4zERurPTAGX8sqnFvhmbtEX1VjJ9wqYu8xWc0y"
    b"ORe/Vbp5iuimBapvi5vwesEOR4mr/hCDCrYpwhX4rLMbZ0lWdoeus7kL8KviW2ZPvCEyv1/B"
    b"Nl0xV1LnrThIlum2gkZGiPs9qIaO+4hyXawcl73UNuJxZ3wgb1c05LeI17iixs6HiqueVWO7"
    b"bdlXJvKIjj/OwLey/LUwR/HvpCPniLdpJA+/UiZyyyfQV7bUJXUYGyWzclQdbV+UwFkP20sg"
    b"3kr93i7Bq1edRp/TyQdXgLEyCYfW0fYySXm3BMM2CViT6zC2mcNkm5xdR9s3RS3UQn/ZUjd3"
    b"/HGMzEqjBYPZ8gEPqbHd1VKwKOrC22RLLpGqzRZulCDVKL3EpS6R2lZRRspEHljw+VnyPR+w"
    b"7Y3nRWqUQT8Jdq+LAylCa/vAzu/iuTYZ53qc2dkDX+Dygp0WYZCs8AqR+kV4S1LmSvTBw/LC"
    b"FSuNa8Wnl8lueFyE4i26LkA/pfNd0SIrtVImfHQ1IxtFCpdNCy7GT3J0ME3lYvajkhJsZkec"
    b"h0VqqMavUVmml0FvXCueaZO429nykhNwDN6Wb3U6nhDlvQ73qaE0+qnGYkhR2uSkaiZekQOf"
    b"fzpca/Ae7pXtVIvnQyTC3SUNtlZ6iHPYhGMbMdQqrvLIEgZVDxslELdI7l83rbI3h0ux6/9g"
    b"nMSe1Y0aapO8fEqjhuqghyjY6WUZvBVfSmG4O5koFZq9yjLYX0r0k8oyWICeeFcKHKVyvajX"
    b"AWUbrsBUcbllVlSQwtv7asvZ6+VQ/IlLm9XBCJmlec3qQAoG34sWa7SIXpXxIvbmKn9l9hFV"
    b"/LKtS69NY4Ko4qfVXlWpxFlSzFuouUXt/zBSjgh+EIFX7+oME/H3txQ5utvFI3J6cwF6uSRg"
    b"RTK/NjnFmi8yfAlObtIYUTzhH4SrRJX2loxukRyyrBL1umf7dQBOkOTqbSm/Pigr0jRqPa/o"
    b"JYMcJy50f5Hb28kLfSOS43k5bui2/1n9C7S9B8+2VLKzAAAAAElFTkSuQmCC"
)

# icons8_grid = PyEmbeddedImage(
#    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
#    b"AUlEQVRoge2WOQ7CMBBFn2gjsdwEOrYTstwuULLcgQYaKDJRLCumQBQf9J9kWRl/FxmNrAfG"
#    b"mE+YAHvgCjyAC7ADxqLZXkbAAXj2rEOcK2WL7OLCEZgDFbCI7yewFcsWqSO8yurrqNdi2SK3"
#    b"CFdZvYr6TSwLwKDnRy6xT7P6LPazWLbIlm4+lzRdWNLN50YsW2REN6P5qoGhWPYtY5qunIE7"
#    b"cKLpQt+zp5A1P4OCdlhRWhS0w4qSoqAdVpQUBe2wouQoaIcV5S9R0A4rSouCdlhRUhS0w4qS"
#    b"oqAdVpQcBe2wovwlCtphRWlR0A4rSoqCdlhRUhS0w4qSo6AdVhRjvsgL9TqhhyhVQOwAAAAA"
#    b"SUVORK5CYII="
# )

# icons8_snap_grid_32 = PyEmbeddedImage(
#    b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAABnRSTlMAAAAAAABupgeRAAAA'
#    b'CXBIWXMAABYlAAAWJQFJUiTwAAABb0lEQVRIidWVMY6CQBSGH5sNdoMHIB7AU1gZGjrEhopA'
#    b'4Q3stLO0IVbewgtQYWzmAlAJBVhSDQ1vCxIzWUZ2Z1kS+Ssmb/i/efMzjIKIMKQ+BnV/P0BZ'
#    b'llmWDQg4Ho+6rg8FoJTKLh8AAH+t3W5HCPE8rxnGcbxarQghmqbZtp0kifAtCQAimqZ5Op0Q'
#    b'MYoiQgi/UE3ThAw5gOM4vLthGI/HoyiK5XIJAOv1uheAMUYp5d0ZY00pz3MAmE6nfTsQuiNi'
#    b'URQSAAAIOfEfwnw+b7vXdS23RWEYvhre73fP83h3xphpmnIhdwDasiyrcb9er8IJvQA/uvcC'
#    b'uK7LuwdB4Pt+U0rT9Dnts322F4tFk+2rISICwH6/v91u5/NZVVXbtququlwudV3PZrPNZtP1'
#    b'q+juoN3QM/Ptdksp/VYVdCCryWTSPBwOh3b1zS6cP0jB1qWvKEp3yMLMX6pnyN3HEBHHn8H4'
#    b'QxYA/lfjz2D8gC9KdCT3eJBRHwAAAABJRU5ErkJggg==')

# icons8_snap_points_32 = PyEmbeddedImage(
#    b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAABnRSTlMAAAAAAABupgeRAAAA'
#    b'CXBIWXMAABYlAAAWJQFJUiTwAAABa0lEQVRIidVVO66CQBSdeXmhHFyAYQEsxNjQKTRUBgp2'
#    b'YAc7sDFU7MI9SGxmA1CBhVBSDQ33FZPoRJCfkPBOBTlzzzlzLzdgAEBz4mdW9eUZFEVxv99n'
#    b'NDidTuv1ei4DSunQ+AghBL3hui4hxLIs/hpF0X6/J4TIsqzrehzHjVUDDABA0zTf9wHger0S'
#    b'QsSgsiw3egwzME1TVN9ut3meZ1m22WwQQoZhfGXAGKOUiuqMMU49Hg+E0Gq1+vYGjeoAkGXZ'
#    b'NAaqqtbVq6qapkUAkCSJZVmiOmNM07TJhlzHbrfj6mEYNh74yqBT/WXQsn2fqMPhIKqfz2fb'
#    b'tjmVpunz2K9YyR8wxnXROuV53u12C4JAkiRd18uyvFwuVVUpiuI4TkPxp8hvVL0Jz5kfj0dK'
#    b'6RuLeRnGWIwp2rRQffBqUb0zfahO9E00IjvHwn6ZSzTo7uzbhMd/RS1o2cFO/P8Z9GrRohdt'
#    b'ZFl/zD6DP/5/oSKa1PBRAAAAAElFTkSuQmCC')

instruction_circle = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAAG4AAABsCAIAAAAE8RCnAAAABnRSTlMAAAAAAABupgeRAAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAAReElEQVR4nO1deVBT1xo/ZGEJCYaASUHD/oQoIgYoFRda"
    b"1LpUHlCsgKjTjhu0irbjWBCt1mFQUUapiPOs1nEEwQVE34Bin+ADl+FFEYUgaAgEA7IYFhNC"
    b"cpOQ98e14RJDSEICieX3D/cs3y/f/bjnfPfcs3xAjoBIJNI82dzcrLPsR0mFAUYMCIL4fD6P"
    b"x5PJZDgcDo/HEwiEiVZqRBiLKdva2hobG1ksVlNTE4/HGxgY4PP5YrEYADA4OIhCoRQ1MRgM"
    b"kUjE4/FEItHV1dXZ2dnLy8vBwcHMzGzi1AdgAk0JQVBtbS2TyXz58uXz58/lcrmNjY2rq6ub"
    b"m5uPj4+dnR3hL5ibm9va2sLGhR9SsVjM5/N7enqam5vLysp6e3vxeLybm5ubm5udnR2FQrG0"
    b"tBz/OzITiUTI2zM3N9cwyeVyp0+frq2sVCp98eJFWVnZ06dPBwcHaTSai4uLjY2Nv78/mUzW"
    b"QQ0IgoRCYXNzM5vNZrPZT548wWKxdDr9888/nzVrllwu14pqLDeIsbCwAAhonsRgtJN9+fJl"
    b"RUVFZWWlWCyePXv2zp0758yZA9fhcDhUKlU3NQAABAKBQqEEBgYCAFgslkAguHv3bkZGBhqN"
    b"9vPzW7x48ezZs8fhBsejgTMYjIsXL75588bHx2fLli1z585Fo9FKeugLWCzW19fX19d3YGCg"
    b"urr69u3bBw8enD59elRUFGxrw8GwpmQwGLm5uVwuNyQk5MCBAyQSCc6H/YlBYWVlNW/ePDqd"
    b"LhQKCwsLjx8/TqFQwsPDg4OD0Wi0IX7RUKZ8/Phxfn5+S0vLkiVLkpKSbGxsDPQYjgpbW9vv"
    b"vvsuPDy8sLAwKyuroKAgMjIyODgY+VagBm1t4L//BQAACwuLf/4TYEY2GAb5gEAQhCxTn5RK"
    b"pSple3p6fv/998ePHy9atGjHjh2ffPKJzlR61AqHw61duzYkJOTWrVtZWVlFRUUJCQm2trbq"
    b"qaRSaVsbhkwGixcDNhvk54PVq2VSqVS1GvodDJSXl69fvz4hIaG+vt5w44oxUnV0dCQlJUVH"
    b"R+fn549KxWDI//MfuVwub2yUl5aqY9ZbA+/r68vJyamoqIiMjPzmm2/kcrm+mPUOMpmcmppa"
    b"WFiYk5NTXV2dkJBgb2+vpn5lJejsBDwecHBQR6tRfzEqqqurd+3a1djYmJaWFhsbi3zhMlqE"
    b"h4enpaWJxeKdO3fevXtXTc3AQBATA7ZulTc3qyPUw1NZUlJy5syZlStXxsbGTsgwQ2c4Ojoe"
    b"OnTo+vXrmZmZ7e3tq1evVlO5t9eMQlHHNla3AzeTjRs3hoSEmJmZKdj04ivGh2rVqlUkEunU"
    b"qVPt7e3btm1DUkkkEkdH7KtXIDcXWFiAqCg5BEngvkvPbuf06dMxMTHPnj1TWbmjo+PAgQOX"
    b"L1/WhEpnNfRFxWazY2Ji9uzZIxQKVVJJJBL1VDr2lRAEHT58mMFgpKWl+fj4qKyTnp6enJzs"
    b"4eHR2dlpoLdiPcLV1TUlJeXt27e7d+/u7u6uqqpiMpnICjKZTD2DLqaEIOjnn3+GIOjo0aPI"
    b"AT8SHR0dDg4OGAyGTqeTyeTBwUEdfmicMW3atPT0dBQK5e+/JiHhdWoqtHTpFh6Pp6G4LqY8"
    b"ePCgUCjctWuXYiD4IbBYbG9v79DPaDa0mHDg8Xgbm088Pa+QSGEkUjgGczgj44yGshgOh6NI"
    b"SKVSDGJkpDJ54cKF2traxMRECILUyNrb21Op1L1798pkss2bN2MwGDniTVOpMtLoGqphOKqa"
    b"mj4s9v0jgsWSnj/vg29zdFlnZ2dFWiwWI0fKHyZzcnLq6upOnDjh4uLC4XDUy27cuFFDZgCA"
    b"VmoYlMrHZwqD0Q1bUyLpDgiYAhOOKqtFuysoKCgqKkpMTHRxcdFcyuSwY8cWqTSxu/sGj1dY"
    b"X/+Nu7ujhoKavqLX1tbm5OT8+OOPvr6+uippGrCzs/vzzzNVVVXt7e0EwoGjR4/6+fl5e3uP"
    b"KqjRU9nf35+RkbFq1arFixePWVXTAJ1OnzVr1sKFC8PDwzMyMvr7+0cV0Wi0k52dLZFIwsPD"
    b"kZUndogyblQREREPHz7Mzs5eu3btKLKjDgZqampCQ0OfPn1qhEOU8aGqr68PDw+vqqpSLztK"
    b"A4eb9ooVKz76LlINPD09IyMjT548qb6Zj2LKvLw8mUy2bt06vepmelizZo2lpWVeXp6aOupM"
    b"2draWlxcvGXLFmNeXjI+MDc3//7774uLi9va2kaqo87tXLlyhUqlzp07F65jQr7CEFTOzs6z"
    b"Zs3Ky8v74YcfVMuO1JW2traGhYU9efJkPDt4I6eqr6//+uuvW1tbVcqO2MCvXr3q4eFBp9NH"
    b"qvA3hKenp7e399WrV1WWqjZlW1tbeXl5dHS0IRUzSURFRZWXl6vsMVWb8urVq56ensilNpOA"
    b"MXPmTBqNpvLBVOF2BgYGOjo6YmKSq6osPv30/Qw6ME1fYQiqVatWpaenR0VFIVckqF7J9vjx"
    b"4y+++KKy0rq7G8yZg8bh0MhSxbW2C730uGZsYqn8/PxwOFxtbe2SJUuQpSoa+LNnz1xd6RAE"
    b"/PxAXd2H5X93YLHYefPmlZaWKuUrm7K/vx+FQtXXkxYsAAEBoLx8vBQ0KQQHBzOZzK6uLmSm"
    b"simrq6s/+yyopsaMyQRFRaCnBwz/wj8JAACg0WhTp069f/8+MlPZ7bBYLH//NY6OYM0amVQq"
    b"/cc/LEpLQViYTCqVmrSv0DtVQEDAvXv3Vq5cqSgd1rOKRKKmpiZ/f8ulSwEajZZKpd7eQCQC"
    b"aDQansg2XV+hd6rg4OCioqKuri7F9PWwBt7U1NTQ0DBzJnD8az7D0hIsWAAm8SGcnZ0JBAKb"
    b"zVbkDJny7du3t27dcnR0nPANMCYBFArl6ura0NAwlAP/OXv23LJlZ4uKAu7cmXL27LkJUs/E"
    b"MGPGDBaLpUhiOBxOX19fVlbn9OlJAAASaUlW1qFPP30+ZcoUQ0/emzqVtbV1XV1dU1MTCoV6"
    b"v6SgoqLC2npoI4a1dWBfX5+Pj48JrQOYECobG5sLFy6gUChnZ+f3SwpoNJpQ+D9FJaHwfzQa"
    b"DUxiNEydOtXW1raxsRFOogAA9vb28fFTW1pSeLw/W1sPx8dPVb82exIKODk5KT64vW/8mzZt"
    b"tLLK+fe/z2VmZk7aUXPgcDihUAhfD412hEKhh4cHgUDQcBG0KQ5R9E5lbm4Ob7YeNtoRiURE"
    b"ItEIxxXGTEUgEHg8Hpw/9IrO5/MnJ2m1BQ6HGxgYgK8nTTkmIPvKIVMKBAI8Hj9BKpkqkE/l"
    b"kNsRi8VyuVzzPtt0fYUeqWQyGQRBym6HSCSKRCKj7eCNk0oikRAIBGW3QyAQ+Hw+mIQ2GBgY"
    b"sLKygq+HmVIgEEyQSqYKoVCIw+Hg6yFT4vH4yadSWwiFQsVTOeR2LC0te3t7J92OVlTwG6Sy"
    b"2yGRSEKh0Gg7eOOkgiBIcSzIUAMnk8mdnZ1yIz5dwAjR3t6u+PozZEoPDw+xWKxmVesklCAQ"
    b"CNra2tzd3eHkkCmJRKK9vX1TU9MEKWZ6ePXqFQaDcXNzg5PDlhQ4OTk1NDQEBATASaPq4I2Q"
    b"6sWLFw4ODvAQUXlJATyFhswxng7eCKnYbPaMGTMUmcOWFHh4eCD3JU9CPZqampCTYMNM6erq"
    b"yuPxOjs7x10r00NnZ2dXV5erq6siZ5gpiUSip6dnZWXluCtmeqisrCSTyQr3DT48pcDd3b24"
    b"uBg+WcR4Ju+NkOrOnTuenp6vX79WlCrv22lvbw8LC+NyuRO7Q8bIqbhc7ldffdXY2IgsVV6q"
    b"SqFQvLy8KioqwCRGRkVFBXwsMTJTxVr0hQsXKq1nnYQS7t+/v+CDxZIqTBkYGNja2opcozUJ"
    b"JFgsFpfLDQoKUspXsW+HQCB4eXkVFhZu3boVWfXjGKKMnermzZs0Go1IJCqXquxZa2pqIiIi"
    b"WCzWhHfwxkb15s2byMjImpoaTbeLent702i0a9euqSz9O6OgoADeNPph0Yg7b2NiYh48eNDc"
    b"3GxAvUwNXV1dZWVlMTExKktHNKW3t7eXl1dubq7BFDM9FBYWzpgxY6Qzh9SdUhAREZGamlpf"
    b"Xw+PNE3aV4ydqr29vaSkJCkpSeWZDaq3iyqu6XS6r6/vH3/8cfjwYfiov4/gy5jOVNnZ2TQa"
    b"zc/PbyTZUU502b59O5fLvXHjhvpqHz1KS0ufP3++fft2NXVGMSWZTI6Jibl8+fKbN2/0qpsp"
    b"gcfjnT9/Pjo6WhF7RSVGP5MtNDTU3d39t99+k/9dJyMzMzOdnJwU2xlHgkZnssXFxe3atevm"
    b"zZthYWGKUpPwFWOnun37dl1d3bFjx0aV1aiTplKp69aty87ODgoKUuyONAlfMUYqHo93+fLl"
    b"devWUanUD3f1aOd2FAgNDaXT6fv27evo6NBQxNTR09Ozf//+wMDA0NBQTeprcapqfHw8hULZ"
    b"t29fT0+PruqZDMRicXp6up2dXXx8vIYiWpjSwsIiOTkZg8H8+uuvEolEJw2NC8gJBiWkpaVh"
    b"sdi9e/dqHg9Du8AH5ubme/bsSU5OTklJ2bBhg9H6CvWVUSjUu3fYGzeAlRW6txcsXw6oVCm8"
    b"FBqudu7cuZcvX/70009YLFaLUA46fIPicrmxsbH79+836Ocsg1JlZsr7+uSDg4P9/fKSkmGl"
    b"58+fj4iIYLPZ2mqly8nv06ZNS01NZTKZSUlJyNiFpgL4ebKxARAE4XDgyy/f58tksiNHjhQV"
    b"FaWkpCAnuDWEjofoOzk5JScnC4VCOOKCbiRGhZ6enqSkJCaTmZaWNnPmTB0YdI9HYGtre+TI"
    b"ESKRuHv37tbWVp15xh+wI3n3DmAwGJEIHD0K+Pz+xMREoVCYlpamw/MIwwz5cVfbGXcikSiT"
    b"yS5evPjs2bNvv/12zpw5Y6HSTVYHKgsLCwyGcuWKma0t6O0FS5cOFhdnMpnMuLg4ZFQMbbXS"
    b"T5i33Nzc0NDQU6dOvXv3boxU2sqOhWpwcJDL5Z44ceLMmTMQBI1RK/2EeYuOjqbRaFlZWU+e"
    b"PNm+fbtJHFfd2Nh47NixgYGBuLi4zz77DIw5UKfeIuZ5eXkdP3780qVLv/zyS2hoaGRkpNIQ"
    b"dWLB4/EyMs40NAx4elrFx39bVlaWn58fEBAQFxeHbMVjgT6ji+JwuE2bNvn7+588efLRo0fr"
    b"169ftGiRkcR/iorag8UewmJJDEb3pUsx8+aRt23bFhQUpMf/t/6ji9JotCNHjuTl5WVlZV25"
    b"cgWO26s4T1QrKn1p9fTpU5FoBQ5HAgBgsSR7+80bNkwJCgrS7xjMIEGtLSwsNm/eHBsbW1hY"
    b"ePr06evXr69evXrhwoU6UOlFKxaLJZFYIupg7ezs4Gp6/F5nwEjMyLi9GRkZBQUFwcHBQUFB"
    b"6j/r6xE8Hq+srOzBgwdtbW1S6aBEEoLFkiSSbkvLYjr9X3r/OYPHB4cNunz58nv37t29e/fC"
    b"hQs0Gi0oKGjBggX66u+VIBAIGAxGaWkpk8mkUCiLFi1atmyZXC7PyPhXQ8OAr6/Vjh2phvhd"
    b"Mzlixkarw6FGDailMslmsx8+fFhRUfH27dvZs2cHBgY6OTmh0WgvLy/d1ICTYrGYw+FwOJyS"
    b"kpKWlhYikTh//vz58+dTqVRtqXS+QTPk9wj4M5qGSS6Xi4w8qJUsBEEcDufRo0d1dXUtLS19"
    b"fX0uLi7w4k8XFxc8Hk8ikfB4PBz2VUmWz+dDECQQCHp7ezkcDovFev36dWtrKxqNplKpFApl"
    b"xYoVNBoNPu9QW63GcoMGcTuaJL29veEVI1Kp9MGDBxAEvXr1isFgXLt2TSwWwysYsFisjY0N"
    b"DocjEAhCoZDP5/P5fJFIpCh1cXFxdnaOiIhwd3enUqlYLFbpUdJWKyN1OxoCg8HAFlm6dCkA"
    b"QC6X83g8iUTC5/MFAgGfz+/u7pZIJLBBCQSCubm5nZ0dgUCwtraGo+wayVhg4k2pBDMzM/g0"
    b"Coe/onGPep6fkeD/A46FUNM4FbsAAAAASUVORK5CYII="
)

instruction_rectangle = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAAGQAAABKCAYAAABNRPESAAAACXBIWXMAAAoSAAAKEgF1aB9/"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAACLZJREFUeJztnW1MW9cZ"
    b"x38xFzAGG2xSsFnAGEzJ28gK7UgatkbTXrqXtJumbV0UbV+2oWra0JZvmSol/dRNm9pu+7Bo"
    b"66QuXZdpnbZoWaYoSOlIIUlDULKkeSEjUJZ2NGM4GNwBtvE+PDYYxy/XxL6AfX8SwvY9vvdw"
    b"nnuec57nnPtnHTqZxAi0AY8CHwY2Ag8Ds2pPsC479cob7MAjiBE+CBQBF4A3gD7gu0BP+LUq"
    b"dIOopwC549uAnUANMAH0hn+uAqGY7zyG9JCfqL2IbpDEmIFtSON/CCgD3kIavw/4r4pzlAAv"
    b"AXvUXlRJu5q5SwPQgfSABsAHnEEM8Dwwt4xz/g8xpGry1SAmoBVp/HbACgwi/v95YCSD13ob"
    b"cIZ/pyRfXFYNi76/CfH1V5DBtxe5k7PFHmAeOKKmcC4aRAGakcbfAawHPCw2frzBN5vUA98D"
    b"utQUzgWXZUHm/B3IIFwKDCCNvw+ZCa0kI4jLUsVaNEhk8N0Zfj2BzHr+AjyLuIfVxiwybr2f"
    b"quBqN0gp8BDS+O3h99cR9/MMcGflqpYW/cgYdjpVwdU2htQgjd8Rfm0A3kTcTz8ws3JVuy8i"
    b"f9MPUxVcSYMoiM+P+P5q4DbS+BeQICxXKAZ+A3wlVUEtXVY1Mvi2AS3haw8gjf8ycFfDumjN"
    b"LBK1pyRbBkmU9xlgdQ++2WQIaAz/TkimXFYZku/ZiQzCJmAYGXxPAeMZus5a5stINviVZIWW"
    b"a5DowbcBCLKY9zlPGvn/POIDwH7g28kKqXFZhYjP70Cmng4k79MLvID0BJ3UvAPUpioUzyAO"
    b"JIe/E1l0mWdx0eWXqAhudBLiQ9z7dKICCotLjpGs520k8v010hN0Msc5ZIXxVLJCbwKPA+Va"
    b"1CjPaQd+kKrQYaRn6GSfQuAPyQoYgLNIN9LJPn4kak84uzUg09UdWtVIhxvAg4kOGoB/ILMp"
    b"HW1I2gEMQADxbQatapTn9JLCICCZ1U2aVEfnPSTWi0vEIGeQWEQNW0ljSVInLl5ShBkO4K9I"
    b"enzJDKCoqGhLZWXlfmBdRUXFLqvVOulyuX6WtarmB98BPhHvgALUud3u7r1797rm5ua2Hzly"
    b"ZPjWrVsfQ6yI0+ncf/PmzT01NTV3vV7vFZPJdH1+fn6XdnXPSfqAzwIn7znS1NTUPTIyEorQ"
    b"3d0ddDqdC3tR3W73OaPR+K7JZHofqFIU5VNGo3GG1b8ev5pRgNfiHmltbX0rFMX8/HzI7XYv"
    b"7NZ2OBy3gZDBYAjW1dV12+32HwEhRVGmkCBHZ3kcJc7M1jA1NXV7eHgxg37ixImg3+/vjbz3"
    b"eDyVwFOKomybnJxsnJmZMVqt1qcDgcAjLG+/q45wFVlVvYfapqamawcPHvR0dXXNulyuM8h2"
    b"G4DiioqKHwM2rWqZRzwBfCPRwQJk/eN19LFBK9YDv4r9MOLDgkgE2QNs0bBS+cw48EDsh7GD"
    b"SjoBos79c5eY4SCeQdo1q47OWWLaO9Ygd9EXq7Skj5hEY7wM7ziyy1An+1whZsyOZxDdbWlH"
    b"ELFBQeSDeAa5pxvpZJUlvSSeQa6RIILUyQpLZrbxDBIK/xRqVaM8Z8kQkWjZ9iKyfVQn+3iI"
    b"ikUSGUQPELVlIWpPZJBzyOqhjjacBbZDYoOkXPPVySgLM9tkW3/+jTzToJN9FtZGkhlEDxC1"
    b"I6IsoaQyiB4gascloCWZQQYRoRYdbTgD7EhmkBCSa9E3MmjDWaA91X7eAeTp2ngUEp47u1yu"
    b"F81ms7e6unoYPX2/HMqRuC9pyspUV1fX09LSMr558+artbW1S1QINmzYcNxkMk0D66uqqv5U"
    b"XFz8RElJyQzw+ezVO2d4EPg6cAjZMfoKspuxLeE3Ghsbj/b09PhDoVAoEAiEdu/e/R5R6ZTa"
    b"2trhgoICv9Pp/BtAeXn5JxVF8aNPlWMpRBq6C3gVeb7wEPA1wKX6LO3t7SPRG+guXrwYamho"
    b"+HnkuNlsnjKZTB4gZLFYvlpeXj5eVlb2T7vdfgqVMhI5igPYDTyH3P3HgAPAx1HRLgm3/MzM"
    b"zASj309MTIQCgUBEibNkenq6zG63/8JsNlfeuXPnt8XFxbMOh+OdQCAwgCgWZFM2b7UQkRCJ"
    b"iChYWZSOPUwm1etcLtcz+/bt84yNjYUGBgZCW7duvQVUhQ9vKi0tHUUkNEqQBZZ8eODHgtzp"
    b"B4DfIXf/c0iPyMhmwqTSGjab7YtWq/Vpn89XNTY29mlEjSCfSCQdewFJwPozfUG1WidHgScz"
    b"ffFVRkS9LiIda0Me0LyA7Ogc1aISareNziGuKVPjQlVBQcF2i8WywePxHAamMnTedIiWjnWH"
    b"P4tIxx5ihdTr1BqkHxEe7k1VUA02m63f7/dbgXWNjY0PDQ0NfTMT501CrHTsA8jg+waZHnzv"
    b"E7UG6UMiyYwYpLKy8tL4+PhHZmdnSyYnJ3ch6ZlMSjqVI2IIHUjsVMaidOz3kWXTNU0JKpWZ"
    b"1WC1WjuNRuMs8GSGovsGJNA6hDwm9nskEGtjjc3+0hEwOwZ8LkPXbQaum0ymaUVRZr1e7xbk"
    b"cWE1RKvXtYffX0Pcz+vAfzJUxxUhnWdBhhDZ7JFlXsuB3ADvAoM2m+3ZiYmJvyNatsmmj9Hq"
    b"dQ4kGItIx75AjqnXpdNDnkK6/6tpXqOkoaHhWGtr6yZFUTh//vzQ0NDQZ4g/s4qVjrUD/yI3"
    b"pWPvGyeQ9vPp9fX1Lx4/ftwfyYmdPn06WF9f/1L4sB2Jcg8Af0QUSw8g0bApI7XOcf6c7hc2"
    b"btzYH4qhubl5HGn8l4FvIamX1aayvSKk+zzhDCk0A6MwA9t8Pl/RjRs3aG5uBmB0dJRgMHgJ"
    b"6Rk6MRSkLrKEiMZJvP8WU4NIBXYiUqiPA0Gv13v05MmTD5eVlZVevnyZzs7OtwcHB79EDsQC"
    b"2SBdN/Eo8FHgpyT+l0E93DsTM1ksli8Eg0HF5/O9hiTpdOKQrkGKkTTKdWTq2YcYYa3+14JV"
    b"x/8BanhVJKRKjdcAAAAASUVORK5CYII="
)

instruction_frame = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADwAAAAxCAYAAACGYsqsAAAACXBIWXMAAAcoAAAHKAGcLxde"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAA9BJREFUaIHtml9IKlkA"
    b"xj/nGpkRQw/e/tFC9meDkKU2kUFCIlq4lDQ99Q/Chy1qKeohDJaFfVpC9m3Zh95TwfVSS8Qt"
    b"ig3SaKg2xPugrawaRF7B1IFlVbKafbh0t61Gu4tT18Hf25zzHfm++cYzoEeC9xB6vd6o0Whe"
    b"KRSK6ouLi/Tp6ekfDMP87HQ6f4PIeGEwGF5Ho9Er7g4OhyPS19f3zXMbzCk0TX/Psuz13bA3"
    b"LC8vnzU1NSmf22euILRa7VckSUr4BP39/dVqtVo0LUtJkqzKJqqoqPh6YmLi1VMYyiUMw8Dt"
    b"drfcHpOmUqm/si1sb28nh4aGSOGsCcPs7Kzf7Xb/Z4xwu92/cxzHu8jj8UCpFM1XGMT29va3"
    b"JpPp7UOTLMtid3cXGo3mw5jVaoVCoUAgEHgyk7nkBcuyf4fD4TfHx8cNEonkZVlZWUkkEsHm"
    b"5iZ8Ph9GR0chkfy7p83NzaG3txderxc6ne4ZrWdnY2Mjvr+//xOvQC6XV3d1de3v7e1xyWTy"
    b"3isqFApxnZ2dXCwW41paWvjeZJ8MMzMzf97NSNy+SCQSIZlM9o6iKMhksns3xGq1YnBwEOXl"
    b"5aivr8fh4WEuinhSpB8jttlsKC0thd1uRzQaxdLSEtRqtVDeBOHRgT0eDyorK7G6ugoASKVS"
    b"UKlUSKfTKCoqEsxgriGyS97j8/kwNTX14Vomk2FsbAx+v18QY0Lx6IZpmr43ZjQac2rmKXh0"
    b"w2KhEFjsFAKLnUJgsVMILHYKgcVOIbDYKQQWO4XAYqcQOJ8wm81QKpXo7u5Ga2sr5ufns67J"
    b"68AAMDIygq2tLRwdHcFiseD6+jqj/qN+l/4U8Xg8sNvt8Hq9GBgYAEFk7jDvG06lUojH45DL"
    b"5djZ2QHDMBn1ed9wW1sbxsfHAQBVVVWw2+2gKIpXn/cNx+NxBAIBuFwuWCwWaLXajPq8brix"
    b"sRFOpxMmkwnFxcWYnJyEXq9HMpmEy+VCNBotlcvl1YlEIsT7IT09Pb8+99+c/5fLy0vObDZz"
    b"NpuNCwaDXDgc5tbX12PT09OrSqXyM9EFXlxc5FiWfXBuYWHhbV1dXUVeP9K3YRgGOp0OJPnw"
    b"2Ruj0ajy+/0/5P2mdcPJyQmam5t55wmCgEql+vLBhtPptGDGhILLcBLphpKSEvJe4GAw+Jqi"
    b"qHeCuBKQmpoaanh4+ItMmng8zr9b5xsNDQ31KysrZ3wbWiwWu6Jp+rvn9plTaJqedDgckbth"
    b"z8/PrwwGwy8ACN5DpflKR0dHF0VRU7W1tZ9LpdKiSCRydnBw8GZtbe1HANw/8RXUX0uyBW8A"
    b"AAAASUVORK5CYII="
)

icons8_measure_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"iElEQVRogdXaS4gdRRTG8d+dZGKUGKNoHIURQdGAYBQXKihqFgomC0UcBEVxFRTc+EDJQnQh"
    b"BCFuJIJmIQq6ifhAxAciiA/CRHQWojEQJOAzPkIk8RGTaRdVl7qMQ9++U3Xn9vyhYaa6+5zv"
    b"dNXUOX16aCdnYBdmMDFiLQvmLHyFKh5fW4LBTGKvFET3+AZnj1DXQJyLfYLwz4SZ6A1mSczM"
    b"edgvCN6FNYLomfh7N6hWB3MhvhOEfoLV81wzoeXBrMP3mv0trMWXDa5bdNbjgCDsHc2eeOtm"
    b"5lL8Igh6Cys1f+KtmZnLcTAKeR3jPed6n/hMjY2Rz8xVOKR+S+3dreroDeaLsjLruRaHo+MX"
    b"NXvydawR8k2F3SUENuF6HIlOn0FH8yc/H6vjfZVQzqwtI7OejfgrOn1WCCKHVfgo2tsr1GZD"
    b"ZxP+Vq5mOhEfRFv7hbJm6EzhqLSccneZlXjPIgdxG/6NTp+MYzn7/wq8Ge/9SagIhs7dOBad"
    b"bptzrmme6GVcyDcVfhRqs6GzGceVyROwHDujrQO4qJjSGu7DbDwelZ8nluGlaOM3oTYbOg9G"
    b"h7O4J47l5IkxPB9tHsRlBTT2ZYu0lB4qYK+D56K9Q7iigM2+PKzsu3UHT0dbR3BNrsAmbI0O"
    b"j+F+ZarRbVIQ1xXQWEsHT0lB3BnHc98Tnoj3/oMbiyitoYPt0lK6d875heQJeEwKYmO+zHrG"
    b"sEP/Fs2gu1V3sziKm4oorWEZXogO/8Qd8vMEPCAt0alMjX1Zjpejw8PYEMdz8gQhgVZCJXB7"
    b"psa+jOMVaSndWsjuZiF5Hhdqs6GyAq8p34O9Swhg1v83i+KcgDcE8b8LO0mJFsyUVBmXqAJq"
    b"OUl6gfkZF8fx3Dxxi/SO8kgRpTWswofSUpqbXReaJ26W3ha35Mus5xShiVw6T2wSEl2Fx4so"
    b"reFUTEdn+4RuYIk8cYPUQdmaqbEvp+Nzqb0yGcdz88QGIXlWQm02dHZHZ3uUawhfLXUVt8vv"
    b"ZTViRtlm8JX4I9rcYZGCoGyb/hIh71RCbTaWrW5ASgSzHr9GGzuFGm0k5ASzTmicVXjVCIPo"
    b"spBgLsAP8Z63hfKmFQwSzPnSx8x3hf5sq2gSzDn4Nl7zvtApbyV1wUxK/6XwsVCjtZr5gjlT"
    b"Kl8+xckjUzcgc7+g7ok/TwuF5pKid2a6heRpI1WUwYTwGXhaKDRbxX939lhmMiGH7QAAAABJ"
    b"RU5ErkJggg=="
)

icons8_group_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"eklEQVRoge2afWhWVRzHP88z5zZnsSdtK02aWWRvVlZkIqUiFiqOBuJ6gVgvUERQCUJlb0ZF"
    b"L4S9/BHRC0FpmZQ0i17slSIxsLIc1nTh1tLYcm5l2bZ2++P3O7t3d/e595znuQuDvnA5z875"
    b"vdxz7j2/8/397uB//LcxHXgE+BroBPYCW4B7gMkOdrLAcmADsAvYD7QA64FlOj4qGAM8BvQD"
    b"Xp7rILDCwtapwDcxdjzgK2TRUsUYYJM6OAQ8AcwCjgRywEXAC8CAyjwZY+tcoEflmoGrgeOB"
    b"cdpeC+zU8QPAzDQn8qAa/hk4O0Zuvjr3gMaI8RzQoePPAaV57IwFXlS5NmTBikYt8hT6gfMs"
    b"5JfoDewDKkNjZkHeJXkPlAAfqPx9DvebF3eosecddN5RneWBviwyOQ/ZIzaYofIdQMbBfyQ2"
    b"q7GLHXQaVefpQN8Z2rfd0X+z6p2SJJj0iE1IbXFw/n1IF2CStj842AnaOi5JMGkiB7Ud6+C8"
    b"XNs/An3mt4sdgLLQfeRF0kRatXUJgyaytQb6WgNjtu97FjhLf//o4D8SVyDv6IeW8iXADtWZ"
    b"FRr7UvsXWdpaqvJbLOVjUY4f+6+zkL9LZbdGjF2lY7uACQl2JiJP0UMWMxUsBAaRs+Rmol/H"
    b"UmC1yh1ColQYGeBt/Oh1ch5/04FvVW5TMTcehWvwedYOYBVQB9QjE9iNz7cuibGTAz5W2T5g"
    b"HUJTFmm7Tvs9lTsi7YnMw1+luKsXoR/5gkMFcCvwt4WtbcBNjGQIkUiKILXIwWYORA85C35C"
    b"qLfBBIT0TQvIrdUb6da+BmANUKN/9wLfIelAn/aVA8cgB+B47etAXukNNhOKwmx14gFdwEqS"
    b"D6Za4H58hrsbOAl4GNk/HkJhFiCsOh/KgMXAZ6oziHA1Z8xAVswD3gSqHPWnAF+o/p/4+6eh"
    b"gHtpRAKIB9zrojgOCZEeQqdds7VpyKY1EwgnTJc72gOYC/yFPJmFtkqr8c+CsgTZMBoQOmKe"
    b"xHvAs8ArSG5hJvQ6PpWxxQ2q20r+XGYIFcCvqjDb0VEdEo0GkU2dC41ngEuRBM0DmnCj51kk"
    b"knnAZUnC9Sr4uYMDkKjVpbrXJ8hOAdotZcO4En8RYvG4Cq50dHC36r1qKT9P5fcQH73CyCEH"
    b"8wES9m6TOljiYByEcnjAOQ46W1XnAkdfZq9VBzvDszpK230OhsuA05Fwvc1B7yNtXSYP/r1N"
    b"DHaGJ1Ki7YCD4fHIpt2PrJQturR1rZL0azvslUyjoteDUIyj8RfCBsdq25nCPQzN6kLkoJqq"
    b"f69CwrAt+pAnMwf4xEI+g8/f6pHCnS0Mn7sTKd0+QOBNeI1kNmpzbcbubFiWkr8BdF8bpzXI"
    b"UykUGaQ2PBkhd7fHyJ6J5BpVSEa5swi/e4jORovCXHxy9wYji9CVwC3AbyrzTJrOi67gITWr"
    b"xUjqWgecGBhrQeJ+JVIRMfxqAHhJxz9FmIRLxEsVM5E6rk22l3S1ATfidsoPQyFPpAR4CHlN"
    b"skh0a0KSoL342V4SqpGnuBS/frUdIZat+ZTSQimwEVnF34HbkPylWMxHQqkH/ELK30Wi8JQ6"
    b"ayf+W0khKEfyfGO/Jl68cJhvHz3AaaPkowR4S/1sHA0HWXyGG/U1Kk3k8HMb1+QuESZ/aMaN"
    b"TxWKFerv5bQNr1HDcSd2mqhGwno3Fvm5C0x96fxA3/u4fZKLwwKkBhZMskwUy1cjHgZbGm8o"
    b"d7u2FercNZPMhznACQyfiPE1aaT4SNhOxBToumOlikfwgDa+rIqDo/avEinAcC8r9uHKbaqQ"
    b"g8uQvwwj61eFoCLQGnumOFgZ46MXCQpDeJR0Ep1/++pAKZJ5Ip0I+TucX7UotOFWKDn88Q8g"
    b"CcatJL/hZgAAAABJRU5ErkJggg=="
)

icons8_ungroup_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"7klEQVRoge2ZTytEURiHH6aUsfJnNUiJLVKiWDM7Imx8DPkO4kOwUUShyQZLZWM/CSsLSVkY"
    b"gyQW50wx5s7ce94z58ziPPVubvc99/c09545514IBAIBQ1qAZWAHyAMFXXl9bEmf09AsALfA"
    b"d426AeY9ZaxKCtiktkB5bQDNHvJGYiJRqnUPeSuygLlEqeacpy6jBXW/S0Xu8DwBLFcIZVqL"
    b"kiDSB83mLTFrcazEXGPvF8k7zv6Hl4hQJvUiCdIkadYBbGKcR/qM2BQRjSUVeRL2/+ZR0iwV"
    b"uRf2WxtLKnIu7P/NmcWxEjOOvVlrzHH2f+SQSxw6T12BQeAZc4lnYMB56giywAfJJd6BGQ95"
    b"qzIFPBBf4gGY9JI0Bh2oTdYr0QKvqJ1hu80LS5coUaSBaWAU6EUJ3ANXwClQrNN1A4FAIB4Z"
    b"1J9iUrK61ysZYBW4AL5QU+wR0B+jtx841j1feoxVHEsNAVtEL0k+gV1gBbUOa9M1qI/t6XMq"
    b"9X4A28BwPQX6UKtUW8v2OCviPpsCKWAN9WnAlUSpCqhbLiWVSAMnHgTKKwe0SkQOGkCiVPum"
    b"EiMNEL68IieBai8fepJ5O6HbpKmL6vsK11UAOk1EQH02KDaARJEanx3ibKy6gAmEs4aAN+AS"
    b"u281A4FAwDM/X3L1Zo+pVYEAAAAASUVORK5CYII="
)

icons8_curly_brackets_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"g0lEQVRoge2awW8MURzHPxonohwQkXTbBlcOEi4cxKWJmzrTSFxJVOImFSHpX6EiPaESJ67U"
    b"AT3gwtWJlUi620raquXwdpnZzLzvb97MMGo+yR66r+/7/f5282bm9/bBBmFTxv/fC5wBjgCH"
    b"gN3AdmABOBaY4TlwGGgBTeAN8BK4D3wM1EzlAPAQWAd+pLxCSdNbB+a63oVwHlj1GJZVSO+1"
    b"Ckzk0AdcER2D2dMcHs8M+h3gXKjBMLAkDG4DI6EGEUaAGeHVBhoh4jeF8ON82RN5IjxvhIi+"
    b"FaIn8qZO4KTwfB0i2hKiO/OmTmCX8GylTfTdR9SVKOs9yEqQ70AJQf4KdSFVoy6katSFVI0N"
    b"X8igmLdcdJAIX8X4tqQ30wo5LsTeyTjhvBfjKtsvBnCtq++Z53JYRhNXhPcCxiUxLYQ+AVuK"
    b"zR5jK65392WY9gk0gFkh0AFOlxI/zji6M53FNX8xLmDry6+VXUGEKUOeNeBidNIXMeE75a6L"
    b"NCa73rJH6S2azQbRsvqPvJ5r0T8udd9QX+VUoTH9XDfkWcHt9MQYxrbYx8uuALebqRb7XWDI"
    b"J6Iuv03cJbIsLJffWxYhyw1xstjsMdQN8QUZnhFPCbFXBQbvR32IY1nEBoXYUlGpE1gW3okP"
    b"jfV2UNWoC6kadSFVoy6kavwXhbTF3LJ+6PGxmDbgK+SDED0oxkNQmqmZfIU8EqJXxXgISlNl"
    b"SqSB/nl6BhgNEe9jFLgjvNqIRsrHBLYDA/OhBrizKEq/A5zN4QG4YlYMZqFY+vLgUw/97Ace"
    b"8GcP1XwD7gH7LCJZe4o9uM2Ho/w+5rQD19WZN5f7mMcdc1oEPuMOBfSOOTUDNf9dfgJIo6Fo"
    b"GBYq0QAAAABJRU5ErkJggg=="
)

icons8_constraint_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAIAAACRXR/mAAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAAG5ElEQVRYhe1YzU9TXROfXlpoq7SB2xYuBWoIMYEFEluF"
    b"CkYTAROsiSGKX5GQWBNjCgnGYDB8KAaFAgISwx8gbnRltAE/0lBDgQ0bV1ihYuIHYIqUK95y"
    b"Wzrv4rxvU6Xw3j70iS74rXpm5sz53TlzpnOOCBHh7wP1pwlExjataLBNKxps04oG4ohSuVyu"
    b"1+t5nhfohaKonTt38jzv8/kETomPj5+cnPz582dkNUbCwYMHI8o3wf37910uV1RTiouLN1JF"
    b"prV///6oFjh79iz5yNHRUeGz9u3b9y/SunjxIgBIpVK5XA4AL168+PO0rl27BgCDg4O7du1q"
    b"bW0tLy8HgEAgsEVakVN+Pebm5lZWViiKQkSpVJqWlkbk5eXlJpPp0KFDdXV1crncZrN1d3fH"
    b"xcURLcdxX79+FYlEJIm1Wm1CQoKg9YREa35+vrCwkKbppKQksuTs7Gy4AcuyKpXqzp07v/mp"
    b"qakBAJlMptFoEhMTu7q6BEZLUN1iWdblcnk8ntzc3OHhYYfDkZ6eHm4g+h9+m3j9+vWhoaGO"
    b"jo7v37+zLDs7OysoVBvVrd8gEokQsbCw0Ol0Tk1NWSyW9TbBYHB90dJqtVqt1mKxKJVKjKqx"
    b"E7KJ09PTFEUNDQ319/cDQFNTE5FzHNfY2EjTdLjDwsLC8fFxYuDxeBiGUalUPp8vLS3t8uXL"
    b"AjdRULTkcnkwGJRKpRaLZX5+/vbt2xKJJCcn5/z58zzPV1dX5+fn37x58+jRowaD4enTp0aj"
    b"sbS09O7du5WVlV6v1+VyJSQkxMXFxcfHxzJaiPjx48e1tTXyu7W1lcytrKxcXV0lwpSUlFBG"
    b"2+12EkK1Wu12u4lwbm7O6/UKjJbQv+rMzEyK+q9xbm4u+bFnzx4SAJZl19bWVldXiVyv1+t0"
    b"OgBgGCZ0OFJSUhQKRYyjFQLHcRKJ5PTp021tbQAwMDCAiF6vVywWt7S0EJukpCQAePnyJQA0"
    b"NDRs5GpLVf7GjRsOhyM0bGxsBACfz4eIAwMDANDX14eIU1NTgUDA7/erVKqUlJSFhQVEtFqt"
    b"IWOCurq64eHhrdKqrq4GgJGRkZCKpunq6urQsK+vz+l0IuLExMSXL18Qsb29/cOHD0TrdrvF"
    b"YvHg4GDI3mg0AsDY2BhuuieRaRmNRkQ8efIkADx8+BARl5eXf/z4wbIsAPT29gaDweXl5VAK"
    b"5+fnk5R4/PgxkSwtLbEsSz7DbDYTDysrK0tLS8XFxQDw/v37TdqnyLRKSkru3bsHAFKpNDMz"
    b"U6VS0TRN03RycjIAKJVKtVqdnJwcFxf37t27iYkJkkmlpaV6vR4RKyoqduzYQdM0wzAAQFGU"
    b"RqMhHhiGIUKdTscwzEa0ItctnudNJtPVq1cRsaqqSiaT8TxPURTHce3t7SUlJXq93ufzBQKB"
    b"7Ozs+fl5AOjq6hodHTWZTABgNptzcnLEYrFCoWhpadHpdFVVVaQRVSgUdrvdZrMdPnz47du3"
    b"/+Qkjo2NAcCxY8d+CS9AZ2dnaEh6mCdPnuj1+lOnTvE8v7i4GG6vVCrb2tpCQ6fTCQBlZWWI"
    b"eODAgeg2MZSM5JB3d3eHVAUFBeHNrkajsVqtoeHi4uLu3bt7enrIcGRkBADevHkT/lUGg4Hn"
    b"edxigfD7/eGq8fFxALDb7V6vNykpSaPRkHN34sQJm82GiL29vQBQX1+PiEVFRb8lUHixiHF3"
    b"WlZWRtP03r17AeDbt2+I6PV6ExMTb926RQzq6+sBoKKighyFjfzEmNbk5CTJy1evXhHJ+jaQ"
    b"cDp+/PgmfrZKi+O42traT58+IaLH48nKylKr1Xl5eQBgtVpnZmYQUavVPnjwABEdDkdRUREA"
    b"kFPZ3NxMnLS3tz979iyWtGZmZgDg+fPniMgwjFwud7vdPM83NDQAgFgsJv2CQqFQKpUAwDAM"
    b"uf80NzcDQEdHByIqFIpLly7FmJZMJuvu7s7OzlapVJ8/fw6pOI579OiR2WymKCovL6+trS38"
    b"3CFiR0cHqWpZWVlXrlyJMS21Wk2iwnFcxCmpqam9vb0RVT09PSQXa2trBdIS2m+Rmr62tpaR"
    b"kZGenr6wsBCuZVk2EAisf1CwWq0ymayzs5MMg8GgwOUENc0ZGRlNTU1ut1skEgUCAZlMJpPJ"
    b"fvEijuwnNzf33LlzEolELBYHg8EzZ84IpLXVW3VNTY3RaPR6vVqttr+/n/y3kCL+fxGDTdwI"
    b"JpNpfHzcZDIhot1uLyoqMhgMEolki25j8DRCGhuCI0eOhC4dsY+W0JcCAAAoKChwu906ne7C"
    b"hQuvX78WfuvaZBURRrrsRvsamJCQMD09nZqaKpfL/X6/kCmbvwZGpvXH8Zc+6W7TigbbtKLB"
    b"X0rrP/laqOkzzGHUAAAAAElFTkSuQmCC"
)

icons8_expansion_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"cElEQVRoge2ZXYiVRRjHf+dkyEYf9mGbbtb6QZS0VlteFJWbGLFebNCFya5ppnSREhhhiXbV"
    b"hUJURCsGrUZFbhvWhUllH0ZJQUkabVRGQVYGaUfb3FoX3T1dPM/0zpkz8+6c3dc9LvSHl/PO"
    b"xzvz/GeeeT7mwP+oCGdUW4As8ARwDGittiAjwXqgqM9J4J7qijM82CTGLJmnEcF7gc/1/UNg"
    b"ECHTVj3R4rGYhMQcYKOWFwMrSchcmeWk+SwHU+wHdgPNwEdOWztwv9YXspx0XESfCcB9wJme"
    b"ti+BnU7dZ8CtKeN16OMiBywBaj1tR4DNyG4OG6soP7TmORbxva1aaWhImacI3Jj2ccyOjLfe"
    b"B4CnSNTiq4jvY/E1sAyYqOUGSo3C+LIvLMQQMRhEPPTtwDwy1nFk1bfo+yzgYWveIc9yJYf9"
    b"GeRMXAu8D1w4RP8cUA9M0vJ04OKIeWYBHwAXAZ3AuxXImIpHkdVahwi/T8v7KCeTA1qAV4G/"
    b"8Ov6QcR6zQ6QOKz9tiIa8KaWm7IkQgqZJqu+CJwAvgN+1vI3wE8Oqe3IToVIkCWROxDr1GzV"
    b"uWTWI4bACLzcIuharanAWuCQ1vcAqwMkAB7TvnUjJRKCTaYI9CGe2z13IfN7trYNWmO4JKIx"
    b"Es9eAN6xyj+oILFOqxd4DjlLBl3Izo4qmnTSPqAbWdG9wAVOv9CONJCo1x79PUxi5UYFORK1"
    b"WokIvxc/GRMJL7DqbBKvIOq0Vcubshb2buD6QFsLycE2Ou2SqdH6KUiYY8ozKCcBcpj7gH7C"
    b"B7sFccbRMKu4K9Deqe3LnXpDZoDErLpopZyEwRZte9DzXQ74hwryGTspusXTnkcO6An83r2G"
    b"hMQ4YCHig+ZafWaqYC6ade6QN19Bks+k3gHYJOYE+lyufb5NGwghsYtSB7hhiG/O136/pfSx"
    b"k7P/yNir8iTwkL5/oY8PlyC6+ivwltPWp+P8guxEJ0L4ZeAR4FxgGuLhbwIWUa5eS5Hcp4Ow"
    b"KZ8PXIqocBtitgFZveOk5wOxzyodc52W12h5u5bNYe3KaL7dULojrcBLukKfAi8GVmMqEn/t"
    b"R3ITG38DbyA7MxeJYntIUt/jiGoWkJ2dT3kq0a4yPKCCusgji1SHZI7zEFdQgjZE9wYRXfSh"
    b"Vic4EGi3sYEkBOlFTHoa6rTvj4H2PLLARWQxGtMGs8m45tXgoA42zdNW7whcj6yasXBnIZng"
    b"hMDcRWBbYN4OIknYA55EEigf2nXAtU697bFD1z1LCYczO7TN5yeM2Y8mYTCTJH92MVsnPIRE"
    b"sVAedpjzdzPwOjBZy+fhD2caES0oAOcE5p3BKQjnjRXaiD92MjC7t8iqc8OZWpIbyTWMMqYj"
    b"FmkQ+JNw2BGKfm0yR/W3myQmG1WsJrHne/AnRWn3WrUkJIr4Q6LMkAOupjw2snNsO8NzdThE"
    b"pJFEnczju9CoAa4YEQPFvTrJMqvOvSi40yr3IVFsMxI72UTqEIu0g8S/dCNXrKHbmQ4kFLlq"
    b"pETcW5TQbcckJCnqp3SV+51f8xSQg23OROh25pRcB4VI2KhD8omdSBRrBB9APPY2ZFd8JtZH"
    b"JnMiXREkfNik3yyJ7O+S+YQIIpXc/Zqc+zVE32NvO0wo7gsAfSgAtwHvATfEClcJESPMROBt"
    b"LX8MPF7hGCHUIM7zMi37MsggYoj8Yb3nkNUyuIbsiExBLKTvrq3oyFGGGCKbkSzP53GHSncr"
    b"wfdIqDPZ0/Y78v/JqOIuJIFaoWXbj+SB55G75NAty7BQ6RmJQY+O+yylep4HXkAIHUEc52kP"
    b"Ozk7gOyI+Uuh4nyi2liA3H3Z3vwo/j94TnvYZMYsCYOFyC3KddUWZEzgX8c29Ub7B663AAAA"
    b"AElFTkSuQmCC"
)

icons8_timer_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAD"
    b"t0lEQVRoge2ZSWgUQRSGP8eoKG5R4xK3oAmCCwqK4nbQg0FBAkH0YED0JIpXNXeXg6gRE0+5"
    b"iholihJEEBE9CerB5RARjGsWiWISjZiQ8fCmyOue7pmumk7mMj80FF1v+6eqq957AwUUUEAB"
    b"MaAJSAL/gB/AG+AWUAtsABL5C80OhkjY8xk4A8zPV4BRkY2Ief4CDcCM/ISZHZrIN+A1MEA4"
    b"oe/A3rxEmgWaSFPq3URgI1AHdBNMqB4oGu1gMyGIiMYE4ADwlXQydxHSsSIB7AOqgDEWetmI"
    b"GEwFLgGDpJOJdWUuKOOHLfSiEjGoAv7gJXPZKtIMqASGlOGLFrqNSq8xos5m0r+dPRY+AzEL"
    b"OW2MwV5giYX+GqAt9ay20NuG93TrAoot9NNwBe8vc9A3/xa4CpTk4iQEx4lpiy1GUgtj6E6A"
    b"zFWGz/8aV0chGAM8Vv7/AqUuhs4qI0PAqgCZEoSEkWsBFrk4C8EWvKty2tZAAu/Zfi+D7H6f"
    b"sx7gKPElhPeV7Y+2djf5gtuVRb7FJ58EngIVViEHY7fP7nob5Vq8e3NSFvmFyEr4yfwGjmF3"
    b"ifoxHjktjc0TNsrNSvFhRJ0jpBMxzyMcP9QUHihbN20UXyvF8xF1EsATwsl0IMWUC84pO6/C"
    b"nAdBFzpdEZ0NAYeQ7RSEOcB13BLBD2o8L0ggjMhkNe6wcPgeOJlhvgxYa2HPoEeNpwQJhBFJ"
    b"qvGgpdMG5JsIQzLDnLNOGJE+NQ78BbI4rQE6A+bagJeW9gCmqXFvkEAYkXY1LnNw3I6k5G3q"
    b"XRtS0/Q72NMxtAcJhBUtrcCK1Hilg2OAZ8Byhr+JF7iR8MfQaqOoL8Rf5Ld+Hof3srW6EDfg"
    b"vQN2xB2dBXb6Yllno5xAmmdG+Vrc0VnghorDOmkE6QAaAwPA0jiji4gKvA2JUy5GFiAJo1OO"
    b"ExNuK//OhRXI5ab3Z1Uc0UVEtc/3pVyMzcRbAXZj13xwRTnwU/ntJMfmA0gvVv8y75AEcKQw"
    b"F8nZtM/quIzXk05mJFamnHQSdXE6KELal9pBN/F+M9V4t5Pp3IyN0QcgdYSfTBL5ByqXo7kC"
    b"7+mkScTexDYoQhplfqeDSNFUSbR0pgi5sW+Q3rg2J5TVSrg2BfYgR/PsgLlepIPyFsl4f6Xe"
    b"T0Oy2JXAVrzFm0EnUvs3O8blhGJkdfSl6fr0I6swfTQJ+FGKdAA/YU/gI5J2BNbhNsil3+RH"
    b"AslMtyM1yDKkiWG2UB/wBTm6nyPl8AukaVFAAQUUEA3/AQrUfmUtuKGSAAAAAElFTkSuQmCC"
)

icons8_timer_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"NElEQVQ4jd3TuUpDQRgF4C9Bg+BraGOigqWFhW+hIi5v4EMIaVwweQofwEYrawsxbo2FWNq4"
    b"N2piMSPcJDNEO/HAwMy/nHvuv/BfsI8XnGMXtVxg+RektzjBIk7RQGVQ0gjmMwr3472CDbzh"
    b"aBBpE/co9dh3sdNjmxXKsJcjq6GNhfg+yKgtYh0fqKacDVwU1M3H4CZGM4RlXGM75bzEZo+t"
    b"iQ5uMJchraOVcrxgpcc2Gsk6+MR0Im8NT0XJ32jrH6PXmNCO706CsKuBQ4X7HcYSCceYiWRn"
    b"Cf+4MKN92NHdlJ+gjCtspZxVoasLKWcGyzFnIhfQwAMmf0A2hUdh6LOoCOv0gCXp3y9FZY84"
    b"xPCgL1eEdfoQZrOO1XjqQs3eo7KBZEVUhQ1o4TmeltCAbM3+Pr4AHQRErwawCkIAAAAASUVO"
    b"RK5CYII="
)

icons8_vga_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"yUlEQVQ4je3SPU5CURDF8d+TaNyMGG1dDZYGG2qN1BhrE1fhIuyAwqAU2OEm/Ag8C+clI8FH"
    b"oKLgn5zcmznJuTOTy46to4hzDxc4Q2PNjBmecI95VbxEiWmoRB8foX6NX4baVWdwEudDCFp4"
    b"wQjnNX7FaW67m17aVDe5w9cUPsV13B9DcIX3Gn+cA8cpsLCcYoWfM+zjc80Rs75wkDv8xluM"
    b"Uo1zhCEGaEZtmQ+TCP3Drc2/TW9xL3CIDo79v6dFSjzjzu/KdmwjPz1gX51NjwzGAAAAAElF"
    b"TkSuQmCC"
)

icons8_input_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"20lEQVQ4jdXRvU0DQRAF4E8WGdJFUAmJzxJluASIfW3gCkCuwBWQkhBQAkSkICGRG0wy4s7n"
    b"Xd/aCCGetNH7mbcz/Cc8YZbh5rjKcLPwJolPNAluGa+PJjy5It+Ci4LAyx0FNjDHS0Hga2g3"
    b"MEoEPuB0aCpOQjsY+CP8amCFhXbJS+mFN9p9NuGpcgPO8IY17jvC7lGOcRead4yHWte47U3t"
    b"X7kKTT0UtqtxcaPS0L3DHjHJcLX8987xnCLWmO7TIDANLzjqEB8O2884vFu4wUp7gNK3wvUB"
    b"Rf4IXzjbQCQgdD/qAAAAAElFTkSuQmCC"
)


icons8_point_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAF"
    b"JElEQVRoge2Za2xURRTHf31ZoQWqjTTUaiyCT9D6flRRxESlKmpiMEJQolTjK2qi0QTxERJN"
    b"6jMhRoNIlPDBRJMqIRgTQyTxATY+0BBF66O0lvqoYCmN2O364ezKmbMzu3vvLvrB/Sc3mb1n"
    b"zn/OuTNz5pxZKKGEEv4XKCsyVwswGzgDOAZoBManZMNAP7Ad+BjYCHwKJItoQ0E4DFgGfIsY"
    b"FeXpBh4BJv/rVitMADqQLx3VAfvsBZ4CJsY1Ju7SuhR4CTjcIxsBPgS2At8hjgLUAM3AScA5"
    b"yJKz+AloB9bHtCtvlAHLgTHcLzoGrAOuAqrz4KkGrgQ6gYSH63GgvMi2/4NK4BUyl8U7wIwC"
    b"eE8ENnh41wJVBfB6UQasNgPtARYH+pcDJwOXAzcDS1LtFqAioLMIGDJjrKG4kZVlZoD+lKEW"
    b"ZwMrgQHCG/tnYBXQ6tGfCfSa/o8Wy4nZwKgi3glMN32mAW+QuXdyPZ3AsYZrKtCn+iSAiwt1"
    b"Yhzu+TACnGb6tAG7sxi7G9iVRT4EXG04W5CQnO7zPf4olzeWmkFvN/JbcGcrCfwOPA3MMoOP"
    b"A84HngR+MzoJ4C7D3W76PBzXiVoz4Ae4IfESjxMrgPo8uA8BnsVdigkkIKRRBmzC/UCT4jhy"
    b"mzHyPCVrShGnZX8CC2OMMR9ZrnoZHqXkZxkb7o4xBptxZ0NjlRkgFIbzwQLDtcbINyrZJ1HJ"
    b"pxjyJUp2PO6SejkquQcv4i4xHdpvMLYcGYX4eqU4BjQo2XIlG8afb0VFA+5h2KFk9bhpzI1R"
    b"iDuU4jYj+5LwMrCoAS5MPTU5+url+o2RfaZkz+XgcfCWUnxdva/HneZrs3C04p7SO5CsN4R5"
    b"hrtRydaq92/7lEMZpi50flRtu4y2BvRrgNdM/6bUu9DB9rn53RSwoQEPQo7UqvaQak8x/foD"
    b"+mfi3ztHIGWwD/3IF/eN9YdqT/AphxwZC/TZZ/rFSbOTgfdVuJmuHqtStRM+5ZAjehbqVNvO"
    b"QCN+bEGqPYteoCugY2dQj6VP9CE8CDnSq9pHq3Yf7hcJbd5h5NTWzvSl3u0N6GiuJNATsGFH"
    b"QN+Lx9gfJXqNTOc/G3Lw1AIXIaVArvD7puLdbGTdSvZEDh4HbbihUNcM96r3CeDUKMQBzMTN"
    b"Fh5UsmZji035s2IistnSykuVbDISRdKy93A3Y1RUAO8qvmHcvXe/ko0imXMkrFME3bi19kO4"
    b"XynSaWugs4gkkgKlUQ58pWTewzAXrjEDLFCyGiR10fLniRaOK5GaRHNsx72km2/k18Xwgwrg"
    b"a0XSg3tQTiez0tuCVIG5cC5yiad1dyGZdRrjkRJXr4rYS9jWCi8YeSvwq+mTBD4CHgDmACek"
    b"DJyDrPf3Pf0HkcimscL0WRTXCZCTVhc2vjR6KvCFx7h8n21k3sosNH02UYT7rWbcsnYfkqlq"
    b"VAP34J+d0DMI3AccbLjmIqWzXnLTCnUijXm4cf4v3KoxjUlI2duJ3ERa4/cgJcJNuKlPGotx"
    b"w34CCTpFxa0ew14le1w/FLnbnUH225U6pGS2/HcWbHUA7WReAQ0Ad5C5RPJBNXJbs9Nwjqbe"
    b"H1BcBvxC5tcbQM6FWcBBWfSrkBD9DJkOJJF91hbVqLiRoAk5AK8IyEeQE/kH9l+X1iF3VscR"
    b"rhLXIzPRE5AfMMxFDsG4oTf9dOHeMv5nuADZrINEC7+ryTwIY6Gof6IgSd4pwOlI6t+EpDVl"
    b"SGXXh6Q9Xchf096ytYQSSighiL8BHpA7bZy+dDAAAAAASUVORK5CYII="
)

icons8_flash_off_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"L0lEQVRoge3aP2sUQRiA8V/UIoVgEBVbEQRBESWFpWjQTxCwvQ/gV9DD2kYsFHvzCSyM9oKJ"
    b"iL2gVVJoY1JpMJ7FenGz7u2/mdvdg3tgi53deed9bpbZ2ZljzpypcLTg2iJ+RWrnMh7iND5G"
    b"ilmJITaxFCHWcWxj9PdYjhCzEsNUox9wMmK8EVYD41ViUdIT6YZDeuYMdnUgAifwLtN40555"
    b"konTqghxZM7hp45FCJdZ879EJyI0l7mCfT0SoZnMa/kSnYpQT+aGyRKdi1BNZgHv9VyEcpm7"
    b"iiV6I8JkmbP4ZIZESN702RnAN+USUxM50rDed6xgI1V2Kjyd5jQVgR3cdlimM0JE6JFMqAg9"
    b"kTkWKc4O7uCN8g+n6wXXvkjeQ62zkjnPG83qHoM2Ek9zVTIxvJ8pD5V53kLuh1hPNR5T5lYL"
    b"uR9wMyeBGDLrLeR+iGcTEgmR2Zc8rq0yKEioqcxaSEILAXWXJd/lebzFVup8SfHQvIeL+ByQ"
    b"z1RYxYNMWd6seXw8bjW7Gqyq95hdaDW7GoxFRqr1TIwVzamQFplpmazIzMrkicykzCSRmZMp"
    b"EhnhXub+vNFsQ5z9mSDKRLLTf3raM0Uirwrq9U5mkshvXCup2yuZSSIvKtbvjUyeyB7O14jR"
    b"C5k8kSYTw85lsiK7ko3RJuQNzZuSjdsDYqxrVeERvjasm7c8+xI/QpOqwrJ/v96W5E8DoYx7"
    b"ZhghVi0GeIpLEWMult8yZ05U/gAXf6UpYAxkvgAAAABJRU5ErkJggg=="
)

icons8_quick_mode_on_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"GklEQVRoge3Zu2sUURiG8V9ijKJVUBsFL40iBEFIoWirYCMqWFkJWqmgEPwHLLWwChGE2CdV"
    b"QLAVsbBMShFvYBQvKOIFlTgWqyyb7OyeuZw9iewDB5bZs/O9Dx9z5oOlT5//gjO4jf2pg1Th"
    b"OH4jw9PEWUqzES80JDK8TxunPNc1JTI8TBunHKP4qVVkqu4ig3XfcAkDmMTaJdcfR65bO+e0"
    b"duLfOpUyVFE24Z32IqMJcxVmSnuJRaxPmKsQhzXfGUvXs4S5CjGEOe0lMtyLUTTGqTWOfR2+"
    b"XxUn1nZ8kd+NDBeTpSvArM4SGY4mSxfISd0lMuxIFTCEDRqnUTeJ7+JPE5W4Iawb86kChtBu"
    b"KMxbM7FCDFX8/SBuWT4U5rEOp7vsWcQjvKqQqzDnhXWi6PqErb2S2IIPkUR6ekzfiSjxBMO9"
    b"kDgkfyisYx3rhQRMRJSY7pUEnI0k8RnbygQaKK3CGHYF7JvA5sB7XsHN0okiMoxfwroxp/p7"
    b"LRp7hUks4mCijEGcECYykSpgKFd1l3iDkaqFYo/UewL2jONj5ByVeaBzN+6rdnL2jLfyJX5o"
    b"HAYrnhGdu3EtXbRiHJAv8VzjP5PaiPmwd3rQL+BrncViiuzOuT6NuxHr1s6MGofClMxbLnI5"
    b"aaISDOKbVol5K3gozGOnVTYU5nFEq8hk2jjlGdOUWFDDUNiNNZHuu4CXeI1Lfz/36bMa+QMe"
    b"3GnvusfBCwAAAABJRU5ErkJggg=="
)

icons8_diagonal_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"90lEQVQ4jdXUr0pEQRiG8Z/4B9wii3obglXWZBItIhhEi02jImxc9BIMYrAZxPUStAsKYjUI"
    b"2r0DYQ3nC8M6Z2EOBn3bPDDPfO934PDXM55hW1hHG68J38UqpvEWbAIHmMJH7oFjDPCC+YSf"
    b"Bn/ATCK7Dn6Uk203lN3E+Ud6IZtL2ElcelKtgGpNV8H7mMzJYHNI1niyXEpkLayMkpXUbOFO"
    b"ta5fmew++H5OttdQdoaxnLA3ouZtpuYAF3UyWKuZrF862XBKZbPYqJOV1mzjUc1XbjLZc/Cd"
    b"nPCwoaybStKldrCIc3wFW8YSPnEZAqrf2ALeo9U/yjfm22E9jSsxrQAAAABJRU5ErkJggg=="
)

laser_cut_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAALKAAACygH/GNH1"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABKtJREFUaIHd2muIVVUU"
    b"wPHfjM6kmY5OYllJakSJmaWmmRVGUvQurOhTZJh9slAq/RAVFERfLEEoiCwKKkEqKqKHkRBF"
    b"WFBRVNCbssyw1CzzMdqHdQ5z5859nHPmnrH6w+Fyzl57n7X22Xvttde+5GM9luWsU5S1eDar"
    b"8NCcjc/BnznrFGUyOrIKt+ds/ACG5KxTlHb05BHOQ0+BOkVpFx2XWTgPg/1FSjNkML/IEP+j"
    b"L5J5juT1Wj04CXdgOw4mvwewo+r3C+yu0cYsjMVI0SmjEqW70IbRidxEbMupX2ZW4gf8hr3C"
    b"kHrXwzXqj65Tb0dy9WAzPsIHuLwsQyq5OFHiTozB0cL3T8FM0cO16EJ3Uicd2u14Fz/r/SKD"
    b"yjP4GycPsJ2lolOuHrBGBRmLrdgoxncRxuN3vNIinQpzg+jNGwvWf06EPZNapdBAeF14r2Ny"
    b"1kvn2fKWa1SQidiFdTnqjMC3+FiO4HAwuF307hUZ5R8U7vbM0jQqyBDh+zdr7kKnYx8eKlup"
    b"okwXC96aBjKpwT+pv9b8K3hADJmz65QvE0PwykHTqCDD8aWItYZVlU3AH8Ll/ieYLwLHu6ue"
    b"v4CdOG6wFRoIj2MPpib3C8WQuuWQaVSQbmwRsVgP9mOTkvYzZW6SdmOD2HdsE6mkpWLhbMYw"
    b"YXipLMRXosfLYBr+EvOsVCaLIO+JEtpO9yXf4YgS2u/HcjFxL8wgOw5fiw1XM27L0W5LaMc7"
    b"oudGNpGdJpRb0ERukpg/aweqXF6mCI+0uoncdGHI+Q1k2vCG2OqWNfcaco/G4QicJgw5r4HM"
    b"kkRmYcs0y0knPlE7HEmZIZScX6d8vMjKvNhq5fIyW/j8e+uUzxSGnFun/Hmxuzy29arlZ5XY"
    b"X5xeo2yWMOScGmXXJWWLylMtH4eLRfJD/bets4Wy1fPoSBHCvKl4BiY3zVwsMZkPiC1vJXOE"
    b"IWdVPX9KLKwnNGm3A8dneH9Txohd38si79uIx0R4cWLFs7nCkLkVzy5Knt3apL1LhSPZrkVf"
    b"bZEYBnvFPntMHbku/Khvwi6dIzOS+xH4Bu+pH7ROxWtJvU36dsKAGSHWjd0iml0h3G81lyUK"
    b"3Jzct4lhlRq2Rt99SiXdYoHdJ5IYS5QYoU/Ak3qPDi6pIbNepEGrz1/GiQX0rqrnHULpX4WR"
    b"q8Vxw6AwX3ipgyK8OKWirBtXNahX2csL8GnSzksGkDrtEGO+2VUrV9WOxXrnT/U2dp7IJO7D"
    b"Z/rHW48mBryvdpjTKRbU6mue6ID0mgrfa3xgU3nV22+Pwn165wUcJRIN+5O6+8X8qnSlN+F6"
    b"9Y8AH8mo19Y2kUhulNVIj9JWCU+yuIFsJdeqnQteLNx0Fl4VRxcrxVett03+Zajs5xL3i4mY"
    b"lS05n9dij1B+QzPBPKe6h8lnyNtiEaU3kbBR9HJW9ibvbUqeU928hqSZ+Wtwqpjs6+Q4ck7e"
    b"d8gNIebWOvnOTSrJbEiZQ6sV7FE7euhHni/SIXz9iuS+Ot4arW9g1yU6argYWjvxeUX5LuGJ"
    b"apH+EeEM9XeefchqSBveEq76ApFRT+lJlExJ//2Q0inWmU6RE6umQ+Mc1tNZFPwH6RsguE5X"
    b"XQUAAAAASUVORK5CYII="
)

laser_engrave_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAACXBIWXMAAALKAAACygH/GNH1"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAA0RJREFUaIHt2UmIHGUU"
    b"wPHf9IwzLmRmnIzBuGA0ByMiEWISBdeDiCIqqPdgjjEJERRFQfCkF/UgBBEUBHFFclJwAVFQ"
    b"3HBFoyIeQozbqEmUUWMnHl41PRZTM/1VV/W00n8oiqp67/vet73ve69I4znsSNQpy6N4qlPh"
    b"kcTCN+L3RJ2ynIGjOhVuJBZ+GMOJOmVpoJkinEKzhE5ZGqLjOhZOodcjUltDejkiw/5HI9Lx"
    b"Gkn1Wk2cidvwK45k98PYn7vvxuw8ZZyHaSwTnTKeGT2BIUxmcqswk2hfx9yOPfgZf4mGFF07"
    b"59GfLNDbn11N7MWHeA/X1NWQuVyVGXEXjseJwvefhXWih+djAlOZTmtqN/Am9mmPSE95En9g"
    b"TZflbBWdckPXFpVkGj/gNTG/y7ASv+CFimwqzSbRmzeV1H9eHHtOr8qgbnhJeK+TEvVa6+yW"
    b"yi0qySr8hqcTdI7DN/hIwuGwF9wqevfaDuUfEO72/NosKsmw8P17Le5C1+IQHqzbqLKsFRve"
    b"QwvItBr8reK9pi+4T0yZCwu+7xBT8LqeWVSSY/CVOGsdnft2Kg4Kl/uf4FJxcLw7934XDuCU"
    b"XhvUDY/hT5ydPV8vptS2JbOoJFP4TpzFmvgb76gpnqkzSJrFKyLumBGppK1i4xyw1KxeagOq"
    b"4ssFvo1VUUFVGZHleFfx4a9oLR4rdvmuo8KqGjIjFvYdiXr34AkRAvQNY/hAe9+Yy9fzvFuP"
    b"9/XZEb7FBSKJkJ9K+YaMiKm4rqqKq84aviVSOTcvIncnXhYj0reM43P/drlzR2QNPhaHy77n"
    b"SryqnVlpNaSB13FR1RV2O7W2ixB3Re79iyLZtil7fju7b8MneCMnPypC5C1d2lOaE0Qe+FM8"
    b"g8u1O2daTLHWwh/N5Maz5wYuxsNixB7Bhp5YvQBDuEzsCZ+J/WRYBFbrcT8uEa52FPfiCzwr"
    b"IsVKdveqWY7Nwugp/CTikBmclr2/UZ/H63lOFpn7I9n9nLoqqvunzUExEivFb4ZddVVUNvG8"
    b"GCMioFqMCcWec0wcKouY1LZ/3xAex9U5oWXS/2YtJT8O4Qqc20UhsyIu75RDFg53Dyj+d1ik"
    b"+31C/QMGDBgwoDr+AWj/qA3v5WpJAAAAAElFTkSuQmCC"
)

icons8_small_beam_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"O0lEQVQ4jb3UzSuEURQG8B8mX1OTJqTUJE1s7EwpSdn4lyxY+q8oH8VCiLJRFpqkECUsEGNx"
    b"72R6vWPuhqduve/5eM655zxd0jCA/sTYJGxiIyWwkEg4llq5OzXwrwm7MIuZVMJlzMXEPLJ5"
    b"TKEvlfARk6jl+GqooI7jrLPdUg7wiUaOr4ELHLbxd0QJd/GUOgUX0INF9GZ857jEGoajbRUr"
    b"mMB0Jv4Nu80ZZlsfQvWXRqoxphWNZocf2M44lzCCItZbCq5HWxm32MpWypMFjAtjuMceXqK9"
    b"iIVIuIPrFMKmzirx/wMP8bsszJwgm32ZcfX4iZqgwTpOhJdmFIPCNY8E/VaErV91IiwLwj7A"
    b"k7DpCl6FF+cpkpSivRs3zeQ8YZ/l2LJoCNd99j2OtoR5eG9DepqY/wPFeP4fX8KRO0UnWEma"
    b"AAAAAElFTkSuQmCC"
)

icons8_image_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"KklEQVQ4jdXUPS8EURTG8d8KCdsJuxHbrGwh2S1UElFRSUjotQqNSqNWKhGN2gcQQU/DVxAS"
    b"LwmFCI23QkIxs8k1uXbXVjzNZM45z39O7txz+OvKZd5LmEFvi/4nHOA2BpzELu5x1SJwCAXM"
    b"4iibvMB6pOtGymEDZ9lEEZ+o/gJWVzX1FqEjDebT52sbwLonHwJj6mwDHgWO4xLPWGkHCmXJ"
    b"OSzhDdtYwDtWM7X9qES85RjwA8tBfDoDncdLWruDnp+Aw2lwMdJ9HXoYfHAM1zjFaKMOvwUD"
    b"zaX5/SA2gBPctQOEKcn5rgWxbuyl3lpY3OrFjkFrqbeQLT6XjFGz0QuhOWwKRi80T0iWw4Pk"
    b"HjZSH0bwiC7JcjjOAmFQsr4qmquEG2xJfsw/0ReGG0QBJgJxVAAAAABJRU5ErkJggg=="
)

icons8_stop_gesture_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"N0lEQVQ4jcXTzytEYRTG8c/4FTJZoSwUGxspGytlYWdvz0LJSrJhJayVhfJHKGLFwoKVslSU"
    b"IiJDQolSDIt7J9cwM3emkafeuu957/me855zXv5BPVjHIqpLhTRiDUe4wyYucYgTjBYLnMEp"
    b"FvCBLixHbG/oQ0u2Y0UOYCsOsBTuP8KVsVViD2fojwOMo0FsYaRcwAtcob4QsBaJUqNkA6fx"
    b"hPFyAOswh0nshrYX3OIRN0gJmgPp34BVke+GcL+DTjTj2ddozEf+HRLMY15gMVrNdRAFZq6S"
    b"wAaSpUSKAu/xiiZsx/SvkVXLaFPSOEZvEQl1C+Yxp8ZwjbYYsAG8F0qgUlC/FCbQ4eeQJzEs"
    b"KNFKjMCqMIVzQaPSoXNmvQvmczZM4JvyPbFEmGF7mFWmgQ/YF7yov9cn1P5B23nSvF4AAAAA"
    b"SUVORK5CYII="
)

icons8_return_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"8ElEQVQ4jdXUPUpDQRSG4SdyEcGAiEXAJoWdO0ghWNoIWllJGgu7LCCFdZp0QgKCiL1iFhCx"
    b"cBcWigTBPyyNaGIxEW4R9V6dQt9qmDnn5YM5M/xHFrAWS7aMexzHkG2hjzaSn0oKmEATNTyg"
    b"m6HvFmc4wUv6IMEAl3jDcLQefCGbQhl7aGAT5+MKV/CEI0xnSDmDFp6x9FnRIi5wmkH4wS6u"
    b"hORjmUMlh7AoTEY1R8+3HOKAcMMxuEYpprAkjFwUJtHDdizhDu6EMfoVCep4xXp608ieJ/I8"
    b"VjGLDanPpJAq6GSUDXEjvOV9POYI8gd4B8NqKf/2uJJfAAAAAElFTkSuQmCC"
)

icons8_home_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"cElEQVQ4jdXUvUodURQF4O9qGvUWEpEENKBYGQiBgBKjXUrzAqJPIIrY21v7CEljFRGE1Aop"
    b"JCGSgLYGwQSCEP+9jX/F2RfGuaPo1cYFw8zZZ+21zz57MTwwGm/BKeE9XmITF/cp+AZfUcEB"
    b"fmKoHqGnmMMpltCNtoidRezFbYQaMYn/WJdazeMd1rCPaTy5TqyMZexi6iZiFB6PwiuRW4NZ"
    b"bKPn5iauoCdyZos2v2PmDmJVzEQuaMhsPMdWHYLbaC8SbMZJHYLHkYurF3+q1ugl9KMvvn9g"
    b"FecZTkN2nT3hnuS/LBYkY49hVJroYo7TJjmjRvAvOnPkV5jA23gm0JvjdOJPkeBGCFRRQod0"
    b"6dmiHQVFN4oEVzGIllhfhOhRhnOUyyljAN+KBD/jEJ/QFLEdyU5VPIuY4HyUfhoLVUJ2yhV8"
    b"wBf8lsxaxgi6gjMQsSVp+hUMx5toKY+WEOnH6zhVa+zt4R9+RZvzkg8fES4Bd6xJfI6CFB4A"
    b"AAAASUVORK5CYII="
)

icons8_bell_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"KUlEQVQ4ja3SvS5EQRQA4E8kCg9Asp1sRLb0k/jrJYRIKIQn8LuFxiNIqLyBqBQK22lEFLZV"
    b"iDdALxHE3ypmbnKzcZndONWdOSffzJx7+OfobKG2hAn04QOP7R46jAt84RlPaOAKq7jFXiq2"
    b"hFccYzC3X8YBPiN+k4Kt4B3bv9QsRnTzL2w5YtWEgw9w/VtBtQUM+oVnl5sT86jH5GkilsUT"
    b"pvMbkxE6xDresJOIdeAFU/nNXjyghi4stICOCCNVak4MtIme4Lwo2Sq6LczpUBE4KzT4MwHN"
    b"pmGpCOvAPXZRid9F6FbEVoow6BaaOxbXlYKb1lKwLOo4wzj2hefne7ohjNdaCkaY9nq86R1m"
    b"hB+VPf8Il6lYPrqb1hnawFw74E/Rg9H/wpLjGzFeVCqYlPuEAAAAAElFTkSuQmCC"
)

icons8_output_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"PUlEQVQ4ja3SOUpDURTG8d9zaATBJgtwaMQhQgoHsNPCDQhuIBsQrHQDWYGN0c4NCA5LULEV"
    b"RCsLbdQuTSSx8IS8PK4Dxg8O3HuG/zl34HcaCPsXDeAIxxjsF5ZhH+2wQ31MmqEeoFZYO3zZ"
    b"X4ATOcBNWKfB+F+nnIxprsOy8H2poR+AD4V9O+HrUfGC51D+oUleZcx+FVxDA6eJ2B52E/6z"
    b"qFkrBtYj0EINmyh9M1kpcmpR0wgGGMad7l/r2CuWE7CViBXz74IFpvAY3XawgWdcJoBXeIqc"
    b"nah5DEaPOtDz2NfRTACbOIj1RRGW/zb3mNd9+ab0txrCe6y3YsK3FFA+oHs3ReX9L4m4UZxg"
    b"puBfwnYifxuLBd+Cz+OPQSU6VlPdfqlqMCr5I6/2Aeyp7Uz4H1bJMILpPqbL6/YDkzdghLDo"
    b"+mMAAAAASUVORK5CYII="
)

icons8_close_window_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"3ElEQVQ4jb3UQU4CMQAF0KdxA3sdbkCMGy/BIWThci7hbUzAeAXOoUFvAB5Alrpo0QJ1Jm0m"
    b"/qRJ+2f6+/ubfAbGWTKfYIZRocYOK2xTcoIPfFWOLRo4j4IzXBY6S3EVNX4ES6+ZwzgVHAxd"
    b"gg9YZ/h1/FYseI85XhPuPXLzjn2glX+9N9zi5Wie+7eFi56DpljiLq6fcN214V8fhd/MFnh2"
    b"mumfyGWYy6wrx7bP4aOQ303C7TNd1jgsHb0Oq7AX3A2g9ZkuGqGCaq+7ERrnoGAboYLGFc5W"
    b"Qp8Oj2+JXWSupLCkIQAAAABJRU5ErkJggg=="
)


icons8_next_page_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"HElEQVQ4jcXUMU5CQRDG8R92UgoeQKDEO1iLKOrVtFQ8gYqFEsMJRHuDxxCJVFjsEsnLewto"
    b"jF+yzZeZf2ZmZ5d/UjWeX+kQPUwwi2cSvfa61QzwiQt00IynE70pHlepehtveMJOIq6GIUao"
    b"pICDCCsveJso5cSW8Yx+EawttJmtrI/zAmhdaL+VB7wT5pPVHj4S0C5us2YpJh3l1p6GHmOc"
    b"9avCWjQLgIvQs0zybsytwEY0ZwnQjzRvubOkuryWT/Ce4+vhck0YXOEmr4oDYQVqGT+1No2Y"
    b"s58HJDynodUX+wX3RTDCbY+EF1BPxDVizCu2UkDC9feFVrrC0Oefw6kwsykeVoEtqiUMe+z7"
    b"+xrjWmJmq6piya/yZ/oCgl5ESq9WShMAAAAASUVORK5CYII="
)

cap_butt_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABwAAAAPCAYAAAD3T6+hAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAAFiUAABYlAUlSJPAAAAAZdEVYdFNvZnR3YXJlAHd3dy5pbmtz"
    b"Y2FwZS5vcmeb7jwaAAAAfklEQVQ4T+2TMQ5AERBE59MpVe5/A5XEGSSuwAWUOtnPRqlE5SUj"
    b"bCSTXQbUcc4RgCsSfbnKM9wOG0opoZTiwmlEzhlaa1hrYYyZ5XN8MUZqrfGhlIJaK++PkVKi"
    b"EAJ576l3uMzOVo3gD7P+husLm8WfZoz0+CgnL/jbuWwI/AHZfOz8osNGAAAAAElFTkSuQmCC"
)

cap_round_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAACEAAAAPCAYAAABqQqYpAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAAFiUAABYlAUlSJPAAAAAZdEVYdFNvZnR3YXJlAHd3dy5pbmtz"
    b"Y2FwZS5vcmeb7jwaAAAAzElEQVRIS81VywmEMBCdKGoDindvnkwbYoXmKiL2YgNJAxYh8tZZ"
    b"XHbB2ZtRHzzI5A1kmF8IP1iWBV3Xoa5rZFkGpRSIyD/392GtRVVVspNvcgDOOaRpKjtcQS6B"
    b"1loWr2Lf97JwJZumEYU4jlEUBcIwFPVTmef54TJJEozjiGmaYIxBEAQHnzOpoiji0dzOX5Rl"
    b"Sduo7hbRPM+0rutueYCUCS7FMAzvTLRt6z0Tf3uCM8Q94T0A5iOm4xF74hEbk4Ng3P53fHDP"
    b"L0p4AczxLpvGSdCBAAAAAElFTkSuQmCC"
)

cap_square_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAACEAAAAPCAYAAABqQqYpAAAAAXNSR0IArs4c6QAAAARnQU1B"
    b"AACxjwv8YQUAAAAJcEhZcwAAFiUAABYlAUlSJPAAAAAZdEVYdFNvZnR3YXJlAHd3dy5pbmtz"
    b"Y2FwZS5vcmeb7jwaAAAAh0lEQVRIS+2UOw6AIBBERwhwDzqODC0F4S7cg1OQFRULI6WoBS+Z"
    b"kN1QTPa3AKCqT2Ht/ZRp4uTfJqSU0FqDc94yY9m24yKlFMUYKaVEzjlijN3+PKnuihpj4L1v"
    b"EZBzRimlRWO4OautoBDCXglr7fBKVHWTJISgOhNvGOi3423mnTiZJg6AFWbye0A3zNrCAAAA"
    b"AElFTkSuQmCC"
)

fill_nonzero = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAATCAYAAACQjC21AAAACXBIWXMAAAMpAAADKQG9Lnl1"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAQ5JREFUOI2t07FKA0EU"
    b"RuHPkAQUEdTSSrCIoHZ2KvgCgiiYwkILIfggljY2voB2PoKItvZaK8QqChIVRDAWO8IaspOJ"
    b"5MAtZuafM7uzd0ljOVRfyonCTXRwOyzhamIuiXm84wML/cKlBOEOxjCK7WEI86+7kpCPMou2"
    b"7IN08Ia52IYRHGIL3z3WZ2R3mOcezR7ZEi5+B/t4zD3JoNVEo/uEGq7/IbvBYtEVlHGE1wRR"
    b"G6eoFMnybKAVkbVCJpkpPEeEL5jutbGoD3eDtIhJ1AcRrnWN70LlWY8c+IdxWRt08IUzTMh+"
    b"vxN8hrWnMN+XhkhvYQ8PIXOQIjzHFZYimRouQzZKFcfSeqsSstX85A/ci1xqR7HjbwAAAABJ"
    b"RU5ErkJggg=="
)


fill_evenodd = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAATCAYAAACQjC21AAAACXBIWXMAAAMpAAADKQG9Lnl1"
    b"AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAASdJREFUOI2t088qRGEY"
    b"x/EPmQlhwRUoi1FYsdHMLShRtizURLkMC8rGhtWsWGhcgkQkyUVQFDv5EyljMe9wTMeZV/nV"
    b"szi/5/v+es95nkOcJkK1VEdk4DRquPivwFIkF6VhPOMFI63g9ojAOXSjC7P/EZh83WIEn6lB"
    b"PKoPpIYnDGUdaMMSZvCR0n/FSZNXRGcK2479xsMCrhM3adRaysH1FO4G5WawgKME9C59XUqh"
    b"1+COMZrCob6Xq3jA5W9Q6D1iC7kM7ktTqGT0K4GJVj/usIfehN+Fbdxj4C+BK76/0TkmMY6z"
    b"hL/8l8Cqn1M8DZX0qrFhPepr0Jj0DvrUf79NvIXebfBbqixjtzCPq8AsxgTu4hBjGUwBB4HN"
    b"VB4b4nYrF9h80vwExRFNC/by8doAAAAASUVORK5CYII="
)

join_miter = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAIAAABLixI0AAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAACL0lEQVQ4jZ3SMWgaURzH8a+aE2tEUZAuBWkIuik4VCmF"
    b"gENKIZ0KDhbMVDN0KAmFop3sGnRwKEiHQkgyGLqUQoeQIUuwUCuUGkICtk6lDjVWmju1eh1s"
    b"Lnrxqpcft9zx/314791D7vf1PttbW5zHC7/gKZgAWWeq1arD4RhAZvgI78F4BavT6YTDYWVR"
    b"GfgO14ErWMlkUoHuwR+4e/6qzyoWi4IgDJouqEGei+iwTk9P5+bmBjUDvIEvYB2yZs3maa1Y"
    b"LKbUVkAEPyN5mclMZeXzF7sJgAiPRiG73X4nHJ5sVSoVq/XfbmbhEApgQJ3J5yWKYiAQUAqv"
    b"4Bs4L0FTWYlEQpl+CG0IjYMmWzs7O8roPDThmQZ0A1b+Y9VqNZfLNRgV4APsgnGob4Rb8AI+"
    b"QQ9qWla/319aWlJqz6EBN8/dBViHQ+jDIazDAlzTsnK5nALdhg48hhhsw0+QYBeewPzE8yqX"
    b"yxaLZTBhg6/Qgw78gNfwABwaZz+j+tRqtaLRqCRJg9ff8Bbq8A4+g6xx9j6f7/7ionpdy8vL"
    b"GvPqmM3mSCSSzWaPj49lWZbPzkaszc3NiYTb7Y7H44VCodFojKxi2Do6OrLZbGP7JpMpFAql"
    b"0+lSqdTr9cZfIsWSJCkYDKoIp9MZjUY3Njbq9fr4/lhrdXVVIbxe79ra2t7eXrvdnkyorP39"
    b"fUEQ/H5/KpU6ODjodrs6iCFrBmg2mycnJx6PZ8o/qBWDLGtdGp0Rxb+5WqWcYv6HwAAAAABJ"
    b"RU5ErkJggg=="
)


join_bevel = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAIAAABLixI0AAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAAB0UlEQVQ4jc3TMWsTcRjH8e9dkxvSTImC24lQ2sFGhcIt"
    b"IZopQ4YGg7h1Kg4e6isQgmQIeQMam1cggRKXgGPokuDY6wvokamSEiqn0v/d3+HsvylNcrlM"
    b"/raD5/lw/J47ZMwIIfL5PFd5Bx48hDUgrlWr1RT0GH7Ba2AFq9/vJxKJEFqHEzgEbQVrPB6b"
    b"pqle6jO4cOfqMYYVBEG1WlXQS7iEp1wnhtVqtdTafTiHD9zI1sbGUpbjOKlUKtxJwBEcQXIK"
    b"Mgzj+2AQbXmel8vl1FodxmDefCnLsnbL5WjLtm218wwu4QUzEt1Xt9vVtPDoZOEUDmZB0Zbr"
    b"utlsNhzVoAvHkFrBEkIUi0U1aoMHj+ZAOlgLrHq9rka3wYM3t4h12IUDGIFcYJVKJbXgTP0r"
    b"wAN4C9/gN/yEr/AqvGxkWZ/AhXuQhwYcQwCn8BHKU/VFdN/pdJ5DACdwBj4M4D08AT3uHaWU"
    b"P/b3z+EL7MHdOcUDuq5bOzsR1p+Li+3NzXlEOp2uVCrtdns0Gkkhor/74XBoGMY0YZqmbdu9"
    b"Xs/zvOu5ZSwpZaPRSCaThUKh2Ww6jjN7SAhNSjm/h3/xfX8ymWQymcVDS1lLxfdvH3f1/K/W"
    b"X6GtRkLtoYR+AAAAAElFTkSuQmCC"
)


join_round = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAIAAABLixI0AAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAABYlAAAWJQFJUiTwAAACBUlEQVQ4jb3SP4iScQDG8a/vnffaayloKEQ4ZDQJ4iGI"
    b"29EfqFGnhqQtBG1saUi4IohuaGhwcSiCNqVQ2hpEL9ShQYe6ITDRFukuSSR4/zTI/S659+29"
    b"t6GHd3lffs8H3ud9MZzn4fb2Giyvc/ANXoAbcAo1m0232w0AEryDT3Aa1pxa0+k0EolwmHuw"
    b"gATg1NJ1PZPJCCgFv+Du4a0zq1wuC+gMfIYGSP9g9ft9RVGE9RLGEOIoJ7Xm83ksFhO126DC"
    b"FVayGY+fyCoUCqJzEX7Ak1XI6/V2dnftrWq16nK5lh0ZuvABNlYtv9+vyLKNNRwOg8Gg6OzA"
    b"PlzAJDZ7LRaLRCIhTt8EFW6YQfZWsVgUR6NwAE8tIBurVquJmTagA51jMy3jgk14YGWNx+NQ"
    b"6OjveQwzuLRKnILr8By+gAFfraxcLic6V0EFcX8e7sAb+AkqtOE+xGHd1JrNZrIsL5thmMAr"
    b"SMMj+Ag6fIfXcAvO2u41GAzEEG/BgH0wYA+ewTXwWGy/fvxpIBCQJEnXdQMO4D00oAF7YJgp"
    b"gKIol7e2zPdKp9MWrZVEIpF8Pl+v1+fzuWEY5la73fZ4TF8FSZKSyWSpVOp2u6qq/tmy/L9a"
    b"rVY0GhWEz+fLZrOVSmUymVhVXIZhNQKapvV6vdFoFA6HU6mU+LhW+ZvlNJL9kf9saZoG/Aa3"
    b"/yM6a1FRBwAAAABJRU5ErkJggg=="
)

icons8_menu_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"zklEQVRoge3YvQ3CMBCG4RdEyRLAAgRahoFBkJCggxUyDTVMkGQLOqSkgMJY+XGExDnoe6Qr"
    b"bLn4fI1PBhEREZHojGr21sD810F6KoBb24EdUA6ktm7wsXeRTVA/4tCaNQEy7LvdVRmw/KoN"
    b"IiIiDn/WmgJ7YGaQpY8COAKPpgMX7F/t0Dq7wf1ZqwxtSWwm3voAPIGFQZY+cuBkHUJERP5X"
    b"wuuxsR4/uip/Z22URhAytFI3uD9rXdtuGZmPrHVfpiuGMWvdrUOIiIiIdKgAK0vhhB7uSF4A"
    b"AAAASUVORK5CYII="
)

icons8_reference = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAIAAACRXR/mAAAABnRSTlMA/wD/AP83WBt9AAAA"
    b"CXBIWXMAAA7EAAAOxAGVKw4bAAADI0lEQVRYhe2Zv08iQRSA35qLQCLNhcqYmBAIgWZXQ2F2"
    b"/QdAIVdZ2FxosITmOsvrroHS7WwsLhQUnvwD7la7EQrYGGhIdmzoFgjGAq4YRG528JadJWDi"
    b"V20mL2++zI83zMBNJhPYPLbWLUDnU2sZPohWLpf7auPo6Kjf77N3ZlkWz/P2/Llcjgyd/Eso"
    b"FKJmrNfrE2bq9To1eSgUIiLpkzgajWYRkiQxDBAFSZJmyUejETXmi8Nc5+fngUCAUWiRhB2n"
    b"Wq1Wy62MG5xq3d7exuNxxs4Mwzg9PXUSSdcSRXFra7rsHh8fAWBvby8cDjNq4e3caDSSySRu"
    b"GY/H9FBiCwiCYI/x+/1PT0/sOxEh5PP57PkPDw+JSFLLsixN0zRNw1NWqVQ0TUMIsTthTNPU"
    b"NK1SqQBAPB7HfVmW9R+tGXicDcPwSmgewzAAIJlMLgr4IIfPhuBWq1OWOBqSdFGudTrr0mq3"
    b"VGq7qsrFdDQqXdSY1FgnMX/XfuPurpQXsZ2c/l5mEGNfW5E3UqnCldIuTc2Kv2pr1CKJFC7z"
    b"+EuuuvZaxU6MJkTWFKvQet0OYiLqNsUKtGpVGQAAxLOTiNscnmp1OrWyxKWxVf6y4NrK8e+t"
    b"RchpTrY1ivnS9RWDFLuWHbHUVpiUALwsp6+lVC1GJZZK6onWWzmdK6VqMXrhvpR6ozVPpHA9"
    b"rfHyT6YR87pAzGq8+vvPWs9EktS3qddmnYmQ+vE6kZt1JkZOzlgX2Ep+NM+8XC8wUqvf7+u6"
    b"ruv6cDgEgGazqes6QmhJr4ULHyGk63qz2QSA4XCI+6K8UhE3Ier11efzeXJVRAhtb2/b8wuC"
    b"QESSh49pmgBwcHAwf9kfDAa9Xm93d3e5MbPR6/VeXl52dnZisRhuGY/HDw8PuNN56Geiqqp+"
    b"vx9/Hx8fK4pimmYwGGTUwt3zPH9/f49bnp+fqe9TTo9qhy8tXuFUK5FIePLs5vCdzKnWzc0N"
    b"z/MMSgAAjUaDuqXs0LXYB+YdFEXhOO79GFIrk8lUq1WicX9/n/3NDQDC4bAgCN1ul2jPZrNE"
    b"Czf5/CvKOZ9ay7ChWn8BFZpXh9qFrO8AAAAASUVORK5CYII="
)

icons8_r_white = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"EElEQVRIieXVy0tVURQG8N+VIoomPRQqTSGopqWDNGdp4wrqbwiKIGhe82gi6aiJ2tNBCI0q"
    b"SocR9BrWyLymRZREFiSVDda+dDjuC6eG9cHmcr671vr2Outx+FdQq2DTgaMYRCc2YREzuI9J"
    b"1P/2Am0YwTJWUqCHmEi/c4lfxjBa/1SgJwX5gVHsz9jU0I2xZFdPz5UFvmAeByr69GEBSzmh"
    b"ck3a8BQt6MVrHMI5rCnYLeIOrossiHo9wneR+ftmNxpJTr0F7pZ497kzhQ0F24PJ/3IzgQ5R"
    b"xNESP5ECXsFxnMAFfEp8OeB4itOeEzmTnMpFboicKvEDif+K9QW+J/GnG0RL4c9B0VHPcjfI"
    b"4AE+J4HOAv9ENM3hnMhOvEq3qILt2Jjs3xX4FbxM8VaJbMHHigJ7cUN0513RbUV8wNac4wsx"
    b"yWU0apI78+jK+EzheeOhmMksdqu2zxo4JnZYETXsETO2SuQedsivEDiPXek8TtwlrC3Z9WBb"
    b"ircK7aK/x0p8roW7RP1WcLFkfxXf0oWzGBYT21fgbqZgJ0u2R/AznY7E9Sf/oWYCxLqui2XX"
    b"6P0B3Jaf4LMi83Uiu7eittnOKqJbbNMFsYuqoD8JLGle06xQXaQ+LopZ7rpa4q8lu1nsqyrQ"
    b"QKtYfo0v4xymRSNM443fX8YhMcxZVJmJdlHkQfHeN4vOmhFtOpkE/wP8AkxqjwP00UznAAAA"
    b"AElFTkSuQmCC"
)

icons8_r_black = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"pElEQVRIid3VvU5UQRgG4AdjY2EMIDQuSm0DAbWmWSsLKQzG1tgYYkVt8AJMDAG8BrXQ1vUe"
    b"jBTGRiJ/W5loozGsiVDMOWaYzOzuodM3meb7e+eb+X74XzAyhM0UFtHGFYziO3bwDm+wf9oL"
    b"TGITPRz1OT1sYKIpwSx2BwRPTxfXhyW4hp8NCerzA/NpwPRPJvEelyJZB0/xJ5KN4hbu4WwS"
    b"4wBz+FrKYjNzu6WSMRbks14vOUzJf/KdSn8fL/ECj3G+kj/M+PTQypE8yhjHJOuJ/G0lP1fI"
    b"ZrkOfCYiaZdSLKBdZfMLexn9zRzJ5YYkXaGaCAWT4m+8mGS8AcEn3BWeZQFjGZuLOcct/f8k"
    b"hwv4WPD7UBvFmeTedRBe4WpBt5sj6QwI+ATb+IwblWwVvwv22Xgt/fskLuEvQtfDSsbn0Mmp"
    b"cQIbGYe6458n8tfCWBoRnjrWrZUICON6P3HoCPskDXSEZ3iQvMCeQmXFmBfq/7RTeG4QQY0Z"
    b"YfM1ITjQYJ/UmBA+e5jNuKZPMw+z41u4LcyqaaG7vwmZdoQd322awb+JYwr7y6huOjb1AAAA"
    b"AElFTkSuQmCC"
)

icons8_bed_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"gklEQVRoge3aTQ5AMBgG4Y+4/6VwrlpZlMZvUqOZJ7Ej6bB4NyIk3TVHRIJf4/bQXSEkPX8H"
    b"VWVnH67eWLAGf3Vfpj956DcMoTGExhCaZgaxmS/istMYQmMIjSE0LjuNy05jCI0hNIbQuOw0"
    b"LjuNITSG0BhC0/SyT5UO8sbuhwFJxxYotkA9FgPEigAAAABJRU5ErkJggg=="
)

icons8_arrange_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAE"
    b"kElEQVRoge3ZW6hWRRQH8J+XU5ZmWpolpl21ILWoLCoiwy4PRSRZRGE9VA/1UGBQUJQPRUVE"
    b"t6d6CBIKDQJLIeiCRaKFoqKF1bGLSWleMjUvqV0eZrZn9v6239n7XDwnOH/44GPvmTX/NTN7"
    b"rf+aoQ996ENP4iLMwXxc3sNcaqMfbsBi/Fv4fYrreo5aNfTHrViljfg+vB5/+5LnyzE99uk1"
    b"aMFMrNVG9E+8jDFJu1GYjR1Ju3W4L9roMRwlONCqjdhOwYGTm/QbITj0e9LvJzyIY7uRbwOG"
    b"xEF/SYhsjuSG9YCd2hiKR7AtGXhjfNaZmTxa2F7r1VvZ2jhJmKU/koG+F2ZzUBeOU/Vbq41x"
    b"0ciexPDqONjAzhhuB/1xI5Yl4/4l5KMJdQydITiQhssVmCHkiCOJaViS8PgbC3Bhs07nY15s"
    b"nHX8CFO7k2lFTBW4ZLz+wfuYkja6AAvjy6zR/GKjXoIpAreU61ycBpu0edqKST3DsRYmyeev"
    b"7YTwuTt5uAZ36N4PuqMYKHBbo43vXjyUNSjLtj8KIfaYI0y2DJmK+FbF0HycQH5j0mGT4OTQ"
    b"7ufbgMGRz4aEzw48ixOrGBiCWYLXmYEteFw3y4eIYXGsLfIr8HDkVhnTsDQxkv52CUs6uqtY"
    b"JxgprP72w4y9UthiTeV/WUbdh9eELD8DXxfezcFZXeDAWGFyikFnJs7UqDCyd7mA1IK78E3S"
    b"cKewD0eVODu94Ox+vIHxHXBgfOy7P7G3VJjQoooYjRfkt3sr7ok+5ErSbXgSwyuQuFYoXVP5"
    b"MBeTK/SdHNumKuITXF2h7wg8JS9iF8PnBUdm44QKBjNcplEZLIzPq7R9D5fUGG8kni448jHl"
    b"W2sXnscpNQbIZvlgYmcRrom/Rcnzg3gbE2vYH4OX5L+jdbgXA9KGzeTz2TUGPF34OPcmdjoj"
    b"x8vslX7sRfQTHPoi6XgAb+LcGgROxYvC6u6K/+sUSOfhLfkV/hI3qVFOlCXE7IN+Vzv1QAFD"
    b"BcVQFRfLK9w0Ic5SMSGWZdT1grBcUDD+Aa6sQbA9XIUP5SdtHh6Tl0xNFUYmGtOM+oPGunyi"
    b"sMcPJO0WK4/7VXGFEHrTvDQH5yRtykRjpjAOBaRH5SPBatyuEAkKmKAxka3ALaqdHvYXlMLK"
    b"pP8evCJk+cNhIO7EV0m/3dGH3LLVLazG4VV5+bBWCOdlp4ctuFs+1O/AM8JpTVUUC6uNhFo9"
    b"3f8dKXVH4TlB2qT1zP3C1hyEB4QTxez9ZmH/11HTZaXugujDIZTJhrqHD8PxBLbKz1a66huE"
    b"im5wDbvFw4dKcqhMyC0RrgqqftBZ+E6PQzOBd1RFG9n1RHoc1CGBOlbj/l+F2zQPBClacLPw"
    b"YVftMyCOkV5P7IlcmgWCdlFW7JSF5s6i7Mi0W4q4snq+Kw+xf07sblVfhddG2YHAljhwlTom"
    b"QzYxvyZ2fot2ju9Cvu0iy7bfJUSy64Bm8r/XHj1lWTqt56tevbUK26pXHQZm9fxybUQPdxm6"
    b"TIhmveoytAzX4zONhdX/4nq6DJfiHUGO16nL+9CHPnQx/gMNJvklKNmh9wAAAABJRU5ErkJg"
    b"gg=="
)

icons8_centerh_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyAQMAAAAk8RryAAAABlBMVEX///8AAABVwtN+AAAA"
    b"AnRSTlMA/1uRIrUAAABbSURBVBiVY2BgYDjAAAaMDwaSZgbRBgwM7A1AuoKBgf8A4wPGP0D6"
    b"A+MDdhD9h/GBPIi2Z3xQbwOk+Rsf/AHRzAcffkCmYeIwdTB9MHOg5sLsgdk70P5ngMQDAOj0"
    b"Q7lGJdVSAAAAAElFTkSuQmCC"
)

icons8_centerv_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyAQMAAAAk8RryAAAABlBMVEX///8AAABVwtN+AAAA"
    b"AnRSTlMA/1uRIrUAAABmSURBVBiVY2AgCOT/QWj7/xC6/n8DCm3DDxGX4YPQcnIQmk8GQvPb"
    b"QGh2Cyj9A0Izf0ClGR9ALTxA2E0g20GggQFM/T8Ap2HiJIADqPajuwvubigN8xeMhvkbFg7o"
    b"4QMLN1g44gUAbSsw0GOTYp0AAAAASUVORK5CYII="
)

icons8_split_table_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"f0lEQVRoge2Zv2sUQRTHPxcVjPEKSaMSSBQUvNPexh+IWMfGwp+n2Ci2IlY25iL4LwiCguLP"
    b"EBTUIMRgY+2PM1pIrNRCBYlGuBMtZg/fbm5m3+waWHPzgYXZ2TffeW95tzM3DwKBQOB/oqS0"
    b"qwCHgSqw3GLTBGaAG8BUit5OYB+wDlhqsfkJvAKuAA2ln1Z6gFGgBfz2uO4A5Q56ZWDMU6sF"
    b"1CNfMjPqOam8HiYm7wEmcuiNuBx1pVYFeA4sie7fAJeBrxb7FcAwsEP0HQCuRe1DmDRp8wQY"
    b"B35Y9FYBx4CN0f0vYAvw2uFzRy7w921MR46mUQLuinET4tlj0X8b3e+zD/MC2+PqSt9j3BcC"
    b"ZzzG7RbjPor+T6J/l4feWTHuns3I9QPqSzih5YNor1xAvRi5vgRFIgRSNBZNILbtQZIK5muk"
    b"YVBhsxVY4zF3LibJvgq3r1mhN/sP9CZtznZdas0An5W2vaSnQwOYU+r1A0NK247I1Kp5jKuS"
    b"nlpVD70a3ZRaIZCiEQIpGiGQoqFdEM8Bp5S2vQqbm/gtiKloAxki5+qaIPdGMEnXpdZF4ici"
    b"LgaBSyk2x4H3Sr09wOk0I20gDcxxjgbNPuoZ5jhUw4DGaNGkVgikaHRFIPJP0WoPzbWi/W0B"
    b"9WK4Ankp2jXiR542SsAJi4Zsn0R/iH3EojFvYhvJssJbTFnhi2PSvcA20bcfuB61DwJXxbMp"
    b"TFnhu0WvHzgKbIjuW5iywrTDZyt1sh/dPGB+oedRDr3zWQKQk4/gX3q7ReeT8zKmLOej1YyC"
    b"cH6YtMXQTZiK02bsu9sm8A5TDH2aorcdUwxdDyyz2MwBLzDpmCmdAoFAoLj8AayZ/luTovAF"
    b"AAAAAElFTkSuQmCC"
)

icons8_keyhole_50 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAADIAAAAyCAYAAAAeP4ixAAAABmJLR0QA/wD/AP+gvaeTAAAC"
    b"jklEQVRoge2Zz0sVURTHP6XhIqSflNEPXQjVzkCKCkJBK7BF4b6df0MQbSIX0aJNENHCla2C"
    b"liHqwiDxRyISlBRRIEkuxIdRZGHvtbjn8obXzH1vpnOn4TlfGOZw7jn3e79zf8y9M5AjR44t"
    b"gW0R/gG5tqfYllpQBB4BQ7UmzACljF4zYQ1ujBBie+pWVOJ/wBlgkIhRFCXEYgEY125RQjS5"
    b"CrM2BxIjF5I11I2QapP9X7ADOA+cxCybi8AksOmDzJeQ68Bd4FCFfxm4ATzRJvQh5A7m/QPw"
    b"BdML34AuoA0YBtqB2x64/8IsZjj0xcy7InlF4CZmeFk0iq8o16WYdfdJ3bNxkpIKeSV59xwx"
    b"DyRmOmbdqQlpkZxfwF5H3BHKvXIwRv1OIZrLb7vcl4A1R9xnoIDZM7VpkWsKKcnd1Rtg9ky7"
    b"xF7XItcU8hbYAPYAFxxx14AG4CvwSYtcU0gBeCr2Q2B3SEwrcF/sYeCnIn8okq5aBzDvjhLm"
    b"aZ8OlF0GVqVsiepDsBKpLr9gtiQfJX8k4J8W3wfgeIJ6U1u1LBaBebFfB/zWfg680yb1IaQB"
    b"6BZ7LOC3dq8HTi9COjHjfwN4GfCPA7+BE8AxbVIfQuwTfwH8CPgLwFxFjBp8ChkNKRutiFGD"
    b"tpBm4KzYYULsPOnR5tYW0oXZuq8Ab0LKpzDbkn3AKU1ibSF2yIxQ3nsFsQlMiH1Rk9iXkDFH"
    b"jJdlWPOoexSztII5s1+NiNsv93PATuC7BrmmkNaAXcsxtgk4DLzXINcUMgn0U37i1bCMkgjQ"
    b"FVICninWFwt186UxF5I11I2QapO9gxTO1TWiw1UYJcRuLwZ126KCYpgzSshjzAe0rA09+3s6"
    b"R44cWxV/AAHro5qkVYvkAAAAAElFTkSuQmCC"
)

icons8_add_new_25 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"7klEQVRIie2VOwrCQBCGP8Vr2FkE8VHFVgTPIVZ23kNSewCxFlSwU7AXbFQkhWDhPYyFE1gX"
    b"E3fXRyH5IPzM7jA/sztLIMOCnBYXgSFQeaPmHugDl6SEORB94JuqRQuaSVW0AxwduigDY6Ce"
    b"ZhIfXwhsHUzyWp2HRVN6wFLU2tmUEtAW/ZqJEz8x0S9epwt4StxUdKCsh8DI1PTMfc59iReY"
    b"vYuF5PsSn206mQAHJW4BDWADrLVOjNE70QlkP0jYf9rJ/0yXrckJWIk68+pOXmE0XZGoB1wd"
    b"TOI3FaUlzfjB/6QvSTWHLmJ2UifDjRsEWFa4krvEMAAAAABJRU5ErkJggg=="
)

icons8_edit_25 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"y0lEQVRIie3UP0oDQRTH8Q9uzmAqu9zBM6TI2qbRKrdKIygKKfQO9skJAoJewhVMUuwbMkqa"
    b"ZTaN7A8ezPxm3vsyfxn0WxWW2GByLsAD9hGffYMqPEXxBtu+QRWeo+g3alxmoHWaeFEAeMQ8"
    b"+iOMcY2r8NYn8joB0goavEZ7p13RPsarvgB1+C+OB18MSLeowU34U3yFv9Ju3QAYAP8VAPcZ"
    b"YBbeLPrFDy3pPYrdnQuQQ24jegfkkDyKz+Bv8of2N016wwI/JZBBnXQAlthpgy5S6SYAAAAA"
    b"SUVORK5CYII="
)

icons8_paste_25 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAA"
    b"3UlEQVRIie3VvU0DQRDF8R+IOoAMJ44IoBl3APVAARSAnfMlJyREJCcZXAAOccwRMEjWaHUL"
    b"J5Ac3JNGqx29e/+dDfbYMp3iAW+4x8lfAw6xRrtR79H/tQ4ww2uqVQTfYoy72K8K3in2uyCz"
    b"dNpcF+G7rPimXZBlmCY4xrwQ0BR68/BPYr/cDN1NkJ1YGzzhpXCQo0JvEf4m5YC9rrFwjqv8"
    b"UVKLx66QGmSNm4qnqnxd/6IBMkAGyJZA8rPSxjrCR4+8UcopqvY/+Wldd01yFhOMe0zxrWdf"
    b"r/egfvoE8sJYB3CAY3oAAAAASUVORK5CYII="
)

icons8_remove_25 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABkAAAAZCAYAAADE6YVjAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"g0lEQVRIie3Vu08UURTH8c+SjQGWVhOkIT4KqLUwsQBChQ3RoK2N/gPWkNBSUFGgiZaGREOl"
    b"nYEE46Mh8gf4qLR0YyBxeQQo5m7cHe/sXsKEil9yM/fOOXO+M+fce4YzUCXBpwdTGAlz+I23"
    b"+FXWi7zEUWTUcb0MwFAI+AJXcSWMcRxgISVINbeeQq1lPRyuG/jWcv87tnETM7kYH/GzE/SH"
    b"eGoeRnzrBb7TnQBwG3PB+Qkmw7gc8R1rsX/FVphf7AYR3uQoBEnVF6wXGXuKDGUqBXLD/1u1"
    b"ggfSzllXyAW8lqWiCapgGSu4XwZkD/fQj/cYxRIe4zlepUBiihX+Fv7gb7A91Z6qUgr/Ge/Q"
    b"iwYWAyxJKZBmDe5iVZbCNSfoW90gFe01mMEE+vyr0akhVQziGR7hEJu4g13ZhuiqfIPMa192"
    b"Hg601+CTLF17ZUCaoJiSAMTT1Xy4FrEVaaATNPYlm9iR1eFDAuASrsl+bFEV9Z4JzIu3+Lwa"
    b"eINZJ0jhuQp1DEu0WE60jG9UAAAAAElFTkSuQmCC"
)
# ----------------------------------------------------------------------
icons8_visit_20 = PyEmbeddedImage(
    b"iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAABmJLR0QA/wD/AP+gvaeTAAAB"
    b"iUlEQVQ4ja3UsUvVURQH8M/LtDIQyfJRDS0ZDoKQW2QQtgQVDfontNRiVGMIDjXlEG2Cow29"
    b"h4pNDWFGa7RUg7a4JErBWyOw4Xce7/bj/d57Zl84cO6553zv93fu79yS1jiNmxiO9VesYruo"
    b"4FBB/DCeooqjWA7rxRKeRE5H6IqiBygViHgUhxUJ+gsPMZOQ35N95iruJiSzuN+OrBuf0BPq"
    b"qngs6+WZOKgSuUcitzsl6MoRXsZxvMYtDGIOL/Abz3El6r5gBDVs1QnyjT2Hb+FfwgqmMYlR"
    b"jQu6Fi3YiJr3dYJ8U3dQDv8nBqIIhvALJ/EjYmXsaoFBrCcEH2S/ykRYb8TOR846TqUEzRTW"
    b"cCGUzWEN42Hv8AybkVNrpxCuYz5ZD+BG2IkkPh+5HeGtxrg1w1Co7RjjWGyx/xJX90MIb2S/"
    b"Sh6jsbdvjMkuJJ3nUsTGioryk5LiOy7iLD5G7A72sPAvCqEPn2WzXA6/v1VBs+cpjyncDn9J"
    b"43E4ECp49T+I6jgW1hZ/AFlFRTnCbQ/nAAAAAElFTkSuQmCC"
)
