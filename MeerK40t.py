from DefaultModules import *
from Kernel import *

kernel = Kernel()

kernel.add_module('K40Stock', K40Stock())
kernel.add_module('SVGLoader', SVGLoader())
kernel.add_module('ImageLoader', ImageLoader())
kernel.add_module('EgvLoader', EgvLoader())
kernel.add_module('SVGWriter', SVGWriter())

from wxMeerK40t import wxMeerK40t
gui = wxMeerK40t()

kernel.add_module('MeerK40t', gui)
kernel.boot()
gui.MainLoop()