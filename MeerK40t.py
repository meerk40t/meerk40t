import sys
from DefaultModules import *
from Kernel import *

kernel = Kernel()

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-z', '--no_gui', action='store_true', help='run without gui')
parser.add_argument('-a', '--auto', action='store_true', help='start running laser')
parser.add_argument('-e', '--egv', type=str, help='writes raw egv data to the controller')
parser.add_argument('-p', '--path', type=str, help='SVG Path command')
parser.add_argument('-i', '--input', type=argparse.FileType('r'), help='input file name')
parser.add_argument('-o', '--output', type=argparse.FileType('w'), help='output file name')
parser.add_argument('-v', '--verbose', action='store_true', help='display verbose debugging')
parser.add_argument('-m', '--mock', action='store_true', help='uses mock usb device')
args = parser.parse_args(sys.argv[1:])

if not args.no_gui:
    from wxMeerK40t import wxMeerK40t
    meerk40tgui = wxMeerK40t()
    kernel.add_module('MeerK40t', meerk40tgui)
kernel.add_module('K40Stock', K40StockBackend())
kernel.add_module('SVGLoader', SVGLoader())
kernel.add_module('ImageLoader', ImageLoader())
kernel.add_module('EgvLoader', EgvLoader())
kernel.add_module('SVGWriter', SVGWriter())

if args.input is not None:
    import os
    kernel.load(os.path.realpath(args.input.name))

if args.path is not None:
    from svgelements import Path
    kernel.elements.append(LaserNode(Path(args.path)))

if args.verbose:
    kernel.device.execute('Debug Device')

if args.mock:
    kernel.device.setting(bool, 'mock', True)
    kernel.device.mock = True

if args.egv is not None:
    kernel.device.pipe.write(bytes(args.egv.replace('$', '\n') + '\n',"utf8"))

if args.auto:
    kernel.classify(kernel.elements)
    kernel.device.spooler.send_job(kernel.operations)
    kernel.device.setting(bool, 'quit', True)
    kernel.device.quit = True

if args.output is not None:
    import os
    kernel.save(os.path.realpath(args.output.name))

kernel.boot()
if not args.no_gui:
    meerk40tgui.MainLoop()