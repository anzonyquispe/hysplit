#!/usr/bin/env python3
"""
Python script to run trajectory and dispersion examples matching the splitr README.
This generates data and plots for comparison with R.
"""

import sys
sys.path.insert(0, "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit")

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# Import pysplit
from pysplit.core.trajectory import hysplit_trajectory, create_trajectory_model
from pysplit.core.dispersion import hysplit_dispersion, create_dispersion_model

# Set working directories
base_dir = Path("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison")
met_dir = base_dir / "met"
out_dir = base_dir / "out"
plot_dir = base_dir / "plots"

met_dir.mkdir(parents=True, exist_ok=True)
out_dir.mkdir(parents=True, exist_ok=True)
plot_dir.mkdir(parents=True, exist_ok=True)

# HYSPLIT binary path
binary_path = "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/pysplit/bin/osx/hyts_std"
disp_binary_path = "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/pysplit/bin/osx/hycs_std"

print("=" * 60)
print("PYSPLIT (PYTHON) TRAJECTORY AND DISPERSION EXAMPLES")
print("=" * 60)
print()

# ============================================================
# TRAJECTORY EXAMPLE (from README)
# ============================================================
print("Running TRAJECTORY example...")
print("Location: 42.83752°N, 80.30364°W (Ontario, Canada)")
print("Date: 2012-03-12, Hours: 0, 6, 12, 18")
print("Duration: 24h forward")
print()

try:
    trajectory = hysplit_trajectory(
        lat=42.83752,
        lon=-80.30364,
        height=50,
        duration=24,
        days=[datetime(2012, 3, 12)],
        daily_hours=[0, 6, 12, 18],
        direction="forward",
        met_type="reanalysis",
        extended_met=False,
        binary_path=binary_path,
        met_dir=str(met_dir),
        exec_dir=str(out_dir),
        clean_up=False
    )

    if trajectory is not None and not trajectory.empty:
        print("Trajectory completed!")
        print(f"Shape: {trajectory.shape[0]} rows x {trajectory.shape[1]} columns")
        print("\nFirst 10 rows:")
        print(trajectory.head(10))

        # Save to CSV
        trajectory.to_csv(base_dir / "python_trajectory_output.csv", index=False)
        print("\nSaved to python_trajectory_output.csv")

        # Summary statistics
        print("\nTrajectory Summary:")
        print(f"  Lat range: {trajectory['lat'].min():.4f} - {trajectory['lat'].max():.4f}")
        print(f"  Lon range: {trajectory['lon'].min():.4f} - {trajectory['lon'].max():.4f}")
        print(f"  Height range: {trajectory['height'].min():.1f} - {trajectory['height'].max():.1f} m")
    else:
        print("No trajectory data returned")

except Exception as e:
    print(f"ERROR running trajectory: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# DISPERSION EXAMPLE (from README)
# ============================================================
print("\n\nRunning DISPERSION example...")
print("Location: 49.0°N, 123.0°W (Vancouver, Canada)")
print("Date: 2015-07-01 00:00, Duration: 6h")
print()

try:
    start_time = datetime(2015, 7, 1, 0, 0)

    dispersion = hysplit_dispersion(
        sources=[{
            "lat": 49.0,
            "lon": -123.0,
            "height": 50.0,
            "rate": 5.0,
            "particle_diameter": 15.0,
            "particle_density": 1.5,
            "particle_shape": 0.8,
            "duration_hours": 2.0
        }],
        start_time=start_time,
        duration=6,
        direction="forward",
        met_type="reanalysis",
        grid_center=(49.0, -123.0),
        grid_spacing=(0.5, 0.5),
        grid_span=(5.0, 5.0),
        binary_path=disp_binary_path,
        met_dir=str(met_dir),
        exec_dir=str(out_dir),
        clean_up=False
    )

    if dispersion is not None and not dispersion.empty:
        print("Dispersion completed!")
        print(f"Shape: {dispersion.shape[0]} rows x {dispersion.shape[1]} columns")
        print("\nFirst 10 rows:")
        print(dispersion.head(10))

        # Save to CSV
        dispersion.to_csv(base_dir / "python_dispersion_output.csv", index=False)
        print("\nSaved to python_dispersion_output.csv")
    else:
        print("No dispersion data returned")

except Exception as e:
    print(f"ERROR running dispersion: {e}")
    import traceback
    traceback.print_exc()

print("\n\nPython examples completed.")
