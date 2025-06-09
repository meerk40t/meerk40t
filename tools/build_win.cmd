echo Building Meerk40t executable v.0.1
echo This script assumes that you have a working python environment where you can run meerk40t from source
echo Making sure plugins are loaded
move meerk40t\external_plugins.py meerk40t\external_plugins.unused
move meerk40t\external_plugins_build.py meerk40t\external_plugins.py

echo Renaming main file for the build
rem pyinstaller struggles with meerk40t.py having the same name as the package meerk40t. Rename for the build
move meerk40t.py mk40t.py
pyinstaller .github\workflows\win\meerk40t.spec
echo Moving files back to their original places
move mk40t.py meerk40t.py
move meerk40t\external_plugins.py meerk40t\external_plugins_build.py
move meerk40t\external_plugins.unused meerk40t\external_plugins.py
