"""
HySplit - Python interface to HYSPLIT atmospheric transport model.

Build with C++ extensions:
    python setup.py build_ext --inplace

Install:
    pip install .

Install with visualization:
    pip install ".[viz]"
"""

import os
import sys
from pathlib import Path

import numpy as np
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class BuildExtWithFallback(build_ext):
    """Build extension with graceful fallback if compilation fails."""

    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"WARNING: Failed to build C++ extension '{ext.name}'")
            print(f"Error: {e}")
            print("The package will still work using Python fallback.")
            print(f"{'='*60}\n")


def get_cpp_extensions():
    """Get C++ extension modules."""
    # Get numpy include directory
    numpy_include = np.get_include()

    # Compiler flags
    extra_compile_args = []
    extra_link_args = []

    if sys.platform == "darwin":
        # macOS
        extra_compile_args = [
            "-std=c++17",
            "-O3",
            "-ffast-math",
            "-march=native",
            "-mmacosx-version-min=10.14",
        ]
        extra_link_args = ["-mmacosx-version-min=10.14"]
    elif sys.platform == "win32":
        # Windows (MSVC)
        extra_compile_args = ["/O2", "/std:c++17", "/fp:fast"]
    else:
        # Linux and others
        extra_compile_args = [
            "-std=c++17",
            "-O3",
            "-ffast-math",
            "-march=native",
            "-fopenmp",
        ]
        extra_link_args = ["-fopenmp"]

    extensions = [
        Extension(
            "hysplit.cpp._parsers",
            sources=["hysplit/cpp/parsers.cpp"],
            include_dirs=[numpy_include],
            extra_compile_args=extra_compile_args,
            extra_link_args=extra_link_args,
            language="c++",
        ),
    ]

    return extensions


if __name__ == "__main__":
    setup(
        ext_modules=get_cpp_extensions(),
        cmdclass={"build_ext": BuildExtWithFallback},
    )
