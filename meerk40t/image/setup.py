from setuptools import setup
from setuptools.extension import Extension
from Cython.Build import cythonize
import numpy as np
print (np.get_include())
ext = Extension("stucki", ["stucki.pyx"], include_dirs=[".", np.get_include()])
# setup(ext_modules=cythonize("stucki.pyx", include_path=[np.get_include()]))
setup(name="stucki", ext_modules=cythonize(ext))
