#!/usr/bin/env python3
"""Test configuration file generation in Python."""

import sys
sys.path.insert(0, "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit")

from pathlib import Path
from pysplit.core.config import set_config, set_ascdata

test_dir = Path("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison/config_test")
test_dir.mkdir(exist_ok=True)

# Create config
config = set_config(numpar=2500, maxpar=10000, tm_pres=1, tm_tamb=1)
ascdata = set_ascdata()

# Write files
config.to_file(test_dir)
ascdata.to_file(test_dir)

print("SETUP.CFG generated:")
print("-" * 40)
print((test_dir / "SETUP.CFG").read_text())

print("\nASCDATA.CFG generated:")
print("-" * 40)
print((test_dir / "ASCDATA.CFG").read_text())
