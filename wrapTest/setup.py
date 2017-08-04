from distutils.core import setup, Extension

setup(
	ext_modules=[Extension("_factorial", ["_factorial.c", "factorial.c"])]
)