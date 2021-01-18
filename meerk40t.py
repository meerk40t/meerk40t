#!/usr/bin/env python

# from meerk40t import main
#
# main.run()

import re
import sys
from meerk40t.main import run
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(run())