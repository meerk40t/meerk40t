@echo off
echo ...
echo If this doesn't find pip or python then you need to get them from https://www.python.org/downloads/
echo ...
echo ...
pip install -r requirements.txt
SET choice=
SET /p choice=Do you want to install optional (but helpful) packages (Y/N)? [N]:
IF NOT '%choice%'=='' SET choice=%choice:~0,1%
IF '%choice%'=='Y' GOTO yes
IF '%choice%'=='y' GOTO yes
:no
echo Okay, skip these for now
goto execute
:yes
pip install -r requirements-optional.txt
:execute
python meerk40t.py
pause