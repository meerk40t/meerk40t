import sys
import argparse
from DefaultModules import *
from Kernel import *

kernel = Kernel()

parser = argparse.ArgumentParser()
parser.add_argument('-l', '--list', type=str, nargs="*", help='list all device properties')
parser.add_argument('-z', '--no_gui', action='store_true', help='run without gui')
parser.add_argument('-a', '--auto', action='store_true', help='start running laser')
parser.add_argument('-e', '--egv', type=str, help='writes raw egv data to the controller')
parser.add_argument('-p', '--path', type=str, help='add SVG Path command')
parser.add_argument('-c', '--control', nargs='+', help="execute control command")
parser.add_argument('-i', '--input', type=argparse.FileType('r'), help='input file name')
parser.add_argument('-o', '--output', type=argparse.FileType('w'), help='output file name')
parser.add_argument('-v', '--verbose', action='store_true', help='display verbose debugging')
parser.add_argument('-t', '--transform', type=str, help="adds SVG Transform command")
parser.add_argument('-m', '--mock', action='store_true', help='uses mock usb device')
parser.add_argument('-s', '--set', action='append', nargs='+', help='set a device variable')
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


if args.list is not None:
    list_name = 'type'
    if len(args.list) != 0:
        list_name = args.list[0]
    if list_name == 'type':
        for v in ('type', 'vars', 'controls'):
            print("Permitted List: %s" % v)
    elif list_name == 'vars':
        for attr in dir(kernel.device):
            v = getattr(kernel.device, attr)
            if attr.startswith('_') or not isinstance(v, (int,float,str,bool)):
                continue
            print('"%s" := %s' % (attr, str(v)))
    elif list_name == 'controls':
        for control_name in kernel.controls:
            print('Control: %s' % control_name)
    exit(0)

if args.set is not None:
    for var in args.set:
        if len(var) <= 1:
            continue  # Need at least two for a set.
        attr = var[0]
        value = var[1]
        if hasattr(kernel.device, attr):
            v = getattr(kernel.device, attr)
            if isinstance(v, bool):
                setattr(kernel.device, attr, bool(value))
            elif isinstance(v, int):
                setattr(kernel.device, attr, int(value))
            elif isinstance(v, float):
                setattr(kernel.device, attr, float(value))
            elif isinstance(v, str):
                setattr(kernel.device, attr, str(value))

if args.input is not None:
    import os
    kernel.load(os.path.realpath(args.input.name))

if args.path is not None:
    from svgelements import Path
    kernel.elements.append(Path(args.path))

if args.verbose:
    kernel.device.execute('Debug Device')

if args.transform:
    m = Matrix(args.transform)
    for e in kernel.elements:
        e *= m

if args.mock:
    kernel.device.setting(bool, 'mock', True)
    kernel.device.mock = True

if args.egv is not None:
    kernel.device.pipe.write(bytes(args.egv.replace('$', '\n') + '\n',"utf8"))

if args.control is not None:
    for control in args.control:
        if control in kernel.controls:
            kernel.device.execute(control)
        else:
            print("Control '%s' not found." % control)
            exit(1)

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