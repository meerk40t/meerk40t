echo Building Meerk40t executable v.0.1
echo This script assumes that you have a working python environment where you can run sefrocut from source
echo Making sure plugins are loaded
move sefrocut\external_plugins.py sefrocut\external_plugins.unused
move sefrocut\external_plugins_build.py sefrocut\external_plugins.py

echo Renaming main file for the build
rem pyinstaller struggles with sefrocut.py having the same name as the package sefrocut. Rename for the build
move sefrocut.py mk40t.py
pyinstaller .github\workflows\win\sefrocut.spec
echo Moving files back to their original places
move mk40t.py sefrocut.py
move sefrocut\external_plugins.py sefrocut\external_plugins_build.py
move sefrocut\external_plugins.unused sefrocut\external_plugins.py
