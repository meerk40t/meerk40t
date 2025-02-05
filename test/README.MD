# Meerk40t test routines

This directory contains code to automatically test the various functionalities
of MeerK40t to avoid regressions after code changes.

These modules are automatically called from the unittest actions after pull requests.

They can be called as well directly via:
    python -m unittest discover test -v
or individually:
    python -m unittest .\test\test_drivers_lihuiyu.py