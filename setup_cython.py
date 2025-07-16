from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy

extensions = [
    Extension(
        "src.models.segment",
        ["src/models/segment.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=['-O3', '-march=native', '-ffast-math'],
        language='c'
    ),
    Extension(
        "src.utils.color_utils", 
        ["src/utils/color_utils.pyx"],
        include_dirs=[numpy.get_include()],
        extra_compile_args=['-O3', '-march=native', '-ffast-math'],
        language='c'
    )
]

setup(
    name='led_animation_engine',
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': 3,
            'boundscheck': False,
            'wraparound': False,
            'cdivision': True,
            'profile': False,
            'embedsignature': True
        }
    ),
    include_dirs=[numpy.get_include()],
    zip_safe=False,
)