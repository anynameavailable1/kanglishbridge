import numpy
from setuptools import Extension, setup
from Cython.Build import cythonize

extensions = [
    Extension(
        "fairseq.data.data_utils_fast",
        ["fairseq/data/data_utils_fast.pyx"],
        include_dirs=[numpy.get_include()],
        language="c++",
        extra_compile_args=["-std=c++11", "-O2"],
    ),
    Extension(
        "fairseq.data.token_block_utils_fast",
        ["fairseq/data/token_block_utils_fast.pyx"],
        include_dirs=[numpy.get_include()],
        language="c++",
        extra_compile_args=["-std=c++11", "-O2"],
    ),
]

setup(
    name="fairseq-cython-components",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": 3}
    )
)
