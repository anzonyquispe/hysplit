#!/usr/bin/env python3
"""Compare R and Python trajectory parsing outputs."""

import pandas as pd
import numpy as np
from pathlib import Path

test_dir = Path("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison")

# Read both outputs
r_df = pd.read_csv(test_dir / "r_output.csv")
py_df = pd.read_csv(test_dir / "python_output.csv")

print("=" * 60)
print("COMPARISON OF R vs PYTHON TRAJECTORY PARSING")
print("=" * 60)

# Show shapes
print(f"\nR DataFrame shape:      {r_df.shape}")
print(f"Python DataFrame shape: {py_df.shape}")

# Show column differences
r_cols = set(r_df.columns)
py_cols = set(py_df.columns)

print(f"\nColumns in R only:      {r_cols - py_cols}")
print(f"Columns in Python only: {py_cols - r_cols}")
print(f"Common columns:         {r_cols & py_cols}")

# Compare common numeric columns
common_cols = ["lat", "lon", "height", "pressure", "month", "day", "hour", "hour_along"]

print("\n" + "-" * 60)
print("NUMERIC VALUE COMPARISON")
print("-" * 60)

all_match = True
for col in common_cols:
    if col in r_df.columns and col in py_df.columns:
        r_vals = r_df[col].values
        py_vals = py_df[col].values

        if len(r_vals) == len(py_vals):
            # Check if values match (with tolerance for floats)
            if np.allclose(r_vals, py_vals, rtol=1e-5, atol=1e-8):
                print(f"✓ {col:12s}: MATCH")
            else:
                print(f"✗ {col:12s}: MISMATCH")
                print(f"  R values:      {r_vals[:5]}")
                print(f"  Python values: {py_vals[:5]}")
                all_match = False
        else:
            print(f"✗ {col:12s}: Different lengths ({len(r_vals)} vs {len(py_vals)})")
            all_match = False

# Check year (R has 24, Python has 2024)
print("\n" + "-" * 60)
print("YEAR COMPARISON (R stores short year, Python expands it)")
print("-" * 60)
print(f"R year values:      {r_df['year'].unique()}")
print(f"Python year values: {py_df['year'].unique()}")
r_year_expanded = r_df['year'].apply(lambda y: y + 2000 if y < 50 else y + 1900)
if np.allclose(r_year_expanded.values, py_df['year'].values):
    print("✓ Years match after expansion")
else:
    print("✗ Years don't match")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
if all_match:
    print("✓ All numeric columns match between R and Python!")
    print("✓ The Python port correctly replicates R's trajectory parsing.")
else:
    print("✗ Some columns don't match - please investigate.")

# Show side by side for first few rows
print("\n" + "-" * 60)
print("SIDE-BY-SIDE COMPARISON (first 5 rows)")
print("-" * 60)

comparison_cols = ["lat", "lon", "height", "pressure"]
print("\nR Output:")
print(r_df[comparison_cols].head().to_string())

print("\nPython Output:")
print(py_df[comparison_cols].head().to_string())
