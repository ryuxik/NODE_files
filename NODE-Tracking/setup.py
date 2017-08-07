from distutils.core import setup, Extension

setup(
	ext_modules=[Extension("_tracking", ["_tracking.cpp", "main.cpp"])]
)