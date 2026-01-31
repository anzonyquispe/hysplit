"""C++ extension modules for HySplit.

This package contains C++ implementations for performance-critical operations.
"""

try:
    from hysplit.cpp._parsers import parse_trajectory_file, parse_pardump_file
    HAS_CPP_EXTENSION = True
except ImportError:
    HAS_CPP_EXTENSION = False
    parse_trajectory_file = None
    parse_pardump_file = None

__all__ = ["parse_trajectory_file", "parse_pardump_file", "HAS_CPP_EXTENSION"]
