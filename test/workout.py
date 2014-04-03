#!/usr/bin/env python

import sys
import glob
import os
import importlib

sys.path.append("scripts")

scripts = glob.glob("scripts/*.py")
scripts.sort()

for script in scripts:
    module = os.path.basename(script).replace(".py", "")
    print("Importing %s..." % module)

    try:
        importlib.import_module(module)
    except Exception as exc:
        print("Error when importing %s!" % module)
        print()
        raise exc

exit(0)