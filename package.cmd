@echo off
echo This will create a new meerk40t.exe! If you are not sure, you can cancel this via Ctrl-C...
pause
if not exist meerk40t.exe goto compile
copy meerk40t.exe meerk40t.exe.old
echo Your old executable is still available as 'meerk40t.exe.old'
:compile
cd meerk40t
move external_plugins.py external_plugins.unused
move external_plugins_build.py external_plugins.py
cd ..

rem pyinstaller struggles with meerk40t.py having the same name as the package meerk40t. Rename for the build
move meerk40t.py mk40t.py
pyinstaller .github/workflows/win/meerk40t.spec
move mk40t.py meerk40t.py

rem Restore original configuration (not really necessary in build environment which is fresh each time)
cd meerk40t
move external_plugins.py external_plugins_build.py
move external_plugins.unused external_plugins.py
cd ..
copy dist\meerk40t.exe .
echo All done.