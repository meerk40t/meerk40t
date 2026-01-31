#!/bin/sh
echo Building Meerk40t executable v.0.1
echo This script assumes that you have a working python environment where you can run sefrocut from source
echo Making sure plugins are loaded
mv sefrocut/external_plugins.py sefrocut/external_plugins.unused
mv sefrocut/external_plugins_build.py sefrocut/external_plugins.py

echo Renaming main file for the build
## pyinstaller struggles with sefrocut.py having the same name as the package sefrocut. Rename for the build
mv sefrocut.py mk40t.py
if test -f venv/bin/pyinstaller; then
    venv/bin/pyinstaller .github/workflows/linux/sefrocut.spec
elif test -f ~/.local/bin/pyinstaller; then
    ~/.local/bin/pyinstaller .github/workflows/linux/sefrocut.spec
else
    pyinstaller .github/workflows/linux/sefrocut.spec
fi
echo Moving files back to their original places
mv mk40t.py sefrocut.py
mv sefrocut/external_plugins.py sefrocut/external_plugins_build.py
mv sefrocut/external_plugins.unused sefrocut/external_plugins.py
echo Renaming file
mv dist/MeerK40t dist/MeerK40t-Linux-Ubuntu-22.04