#!/bin/sh
echo Building Meerk40t executable v.0.1
echo This script assumes that you have a working python environment where you can run meerk40t from source
echo Making sure plugins are loaded
mv meerk40t/external_plugins.py meerk40t/external_plugins.unused
mv meerk40t/external_plugins_build.py meerk40t/external_plugins.py

echo Renaming main file for the build
## pyinstaller struggles with meerk40t.py having the same name as the package meerk40t. Rename for the build
mv meerk40t.py mk40t.py
if test -f venv/bin/pyinstaller; then
    venv/bin/pyinstaller .github/workflows/linux/meerk40t.spec
else
    pyinstaller .github/workflows/linux/meerk40t.spec
fi
echo Moving files back to their original places
mv mk40t.py meerk40t.py
mv meerk40t/external_plugins.py meerk40t/external_plugins_build.py
mv meerk40t/external_plugins.unused meerk40t/external_plugins.py
echo Renaming file
mv dist/MeerK40t dist/MeerK40t-Linux-Ubuntu-22.04