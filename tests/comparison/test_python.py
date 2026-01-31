#!/usr/bin/env python3
"""Python script to test trajectory_read and output CSV for comparison."""

import sys
sys.path.insert(0, "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit")

import pandas as pd
from pathlib import Path

# Import pysplit
from pysplit.io.readers import trajectory_read

# Set working directory
test_dir = Path("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison")

# Read trajectory file
print("Reading trajectory file with pysplit...")
traj_df = trajectory_read(test_dir)

# Print summary
print(f"\nDataFrame dimensions: {traj_df.shape[0]} rows, {traj_df.shape[1]} columns")

print("\nColumn names:")
print(list(traj_df.columns))

print("\nData types:")
print(traj_df.dtypes)

print("\nFirst few rows:")
print(traj_df.head(15))

print("\nSummary statistics:")
numeric_cols = ["lat", "lon", "height", "pressure"]
available_cols = [c for c in numeric_cols if c in traj_df.columns]
if available_cols:
    print(traj_df[available_cols].describe())

# Write to CSV for comparison
output_path = test_dir / "python_output.csv"
traj_df.to_csv(output_path, index=False)
print(f"\nOutput written to {output_path}")
