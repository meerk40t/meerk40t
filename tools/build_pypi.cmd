@echo off
echo Build and upload a package for PyPi
mkdir dist
mkdir old_dist
move dist\* old_dist
python setup.py sdist bdist_wheel --universal
twine.exe upload dist\* --repository MEERK40T