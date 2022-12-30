#!/usr/bin/env python


import re
import sys

from meerk40t import main

if __name__ == "__main__":
    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])
    sys.exit(main.run())
