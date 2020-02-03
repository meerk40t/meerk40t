from DefaultModules import *
from Kernel import *

kernel = Kernel()

from wxMeerK40t import wxMeerK40t
meerk40tgui = wxMeerK40t()
kernel.add_module('MeerK40t', meerk40tgui)
kernel.add_module('K40Stock', K40StockBackend())
kernel.add_module('SVGLoader', SVGLoader())
kernel.add_module('ImageLoader', ImageLoader())
kernel.add_module('EgvLoader', EgvLoader())
kernel.add_module('SVGWriter', SVGWriter())

kernel.boot()
meerk40tgui.MainLoop()