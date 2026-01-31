#!/usr/bin/env python3
"""
Python Performance Benchmark for hysplit
This script benchmarks various components to identify bottlenecks
"""

import sys
sys.path.insert(0, "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit")

import time
import csv
import tracemalloc
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import numpy as np

from hysplit.core.trajectory import hysplit_trajectory
from hysplit.core.config import set_config, set_ascdata
from hysplit.io import trajectory_read

# Configuration
base_dir = Path("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison")
met_dir = base_dir / "met"
out_dir = base_dir / "out_benchmark_py"
results_file = base_dir / "benchmark_python_results.csv"
binary_path = "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/hysplit/bin/osx/hyts_std"

out_dir.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("PYTHON (hysplit) PERFORMANCE BENCHMARK")
print("=" * 70)
print()

# Benchmark parameters - matching R exactly
LOCATIONS = [
    {"lat": 42.83752, "lon": -80.30364},  # Ontario
    {"lat": 43.65107, "lon": -79.34702},  # Toronto
    {"lat": 45.50169, "lon": -73.56725},  # Montreal
    {"lat": 49.28273, "lon": -123.12074}, # Vancouver
    {"lat": 51.04532, "lon": -114.05719}, # Calgary
]

DAYS = pd.date_range("2012-03-10", "2012-03-15", freq="1D").tolist()
HOURS = [0, 6, 12, 18]
DURATION = 48  # hours

total_runs = len(LOCATIONS) * len(DAYS) * len(HOURS)
print("Benchmark Configuration:")
print(f"  Locations: {len(LOCATIONS)}")
print(f"  Days: {len(DAYS)}")
print(f"  Hours per day: {len(HOURS)}")
print(f"  Duration: {DURATION} hours")
print(f"  Total trajectory runs: {total_runs}")
print()

# Initialize timing results
timing_results: List[Dict[str, Any]] = []

def add_timing(component: str, operation: str, time_sec: float):
    timing_results.append({
        "component": component,
        "operation": operation,
        "time_seconds": time_sec
    })

# ============================================================
# BENCHMARK 1: Configuration Generation
# ============================================================
print("BENCHMARK 1: Configuration Generation")
print("-" * 50)

config_times = []
for i in range(100):
    start = time.perf_counter()
    config = set_config(numpar=2500, maxpar=10000)
    ascdata = set_ascdata()
    end = time.perf_counter()
    config_times.append(end - start)

mean_config_time = np.mean(config_times)
print(f"  Mean config generation time: {mean_config_time * 1000:.3f} ms")
add_timing("config", "set_config", mean_config_time)

# ============================================================
# BENCHMARK 2: Meteorological Data Check
# ============================================================
print("\nBENCHMARK 2: Meteorological Data Check")
print("-" * 50)

met_files = list(met_dir.glob("RP*.gbl"))
print(f"  Available met files: {len(met_files)}")

# ============================================================
# BENCHMARK 3: Full Trajectory Runs
# ============================================================
print("\nBENCHMARK 3: Full Trajectory Model Runs")
print("-" * 50)

total_start = time.perf_counter()
all_trajectories = []
run_times = []
run_count = 0

for loc in LOCATIONS:
    for day in DAYS:
        print(f"  Running: {day.strftime('%Y-%m-%d')} at {loc['lat']}, {loc['lon']}... ", end="", flush=True)

        run_start = time.perf_counter()

        try:
            trajectory = hysplit_trajectory(
                lat=loc["lat"],
                lon=loc["lon"],
                height=50,
                duration=DURATION,
                days=[day],
                daily_hours=HOURS,
                direction="forward",
                met_type="reanalysis",
                extended_met=False,
                binary_path=binary_path,
                met_dir=str(met_dir),
                exec_dir=str(out_dir),
                clean_up=True
            )

            run_end = time.perf_counter()
            run_time = run_end - run_start
            run_times.append(run_time)
            run_count += len(HOURS)

            if trajectory is not None and not trajectory.empty:
                all_trajectories.append(trajectory)

            print(f"done in {run_time:.2f} sec")

        except Exception as e:
            print(f"ERROR: {e}")

total_end = time.perf_counter()
total_trajectory_time = total_end - total_start

print(f"\n  Total trajectory runs completed: {run_count}")
print(f"  Total trajectory time: {total_trajectory_time:.2f} seconds")
print(f"  Mean time per day-location: {np.mean(run_times):.2f} seconds")
print(f"  Mean time per individual run: {total_trajectory_time / run_count:.3f} seconds")

add_timing("trajectory", "total_runs", total_trajectory_time)
add_timing("trajectory", "per_run_mean", np.mean(run_times) / len(HOURS))

# ============================================================
# BENCHMARK 4: File Parsing (trajectory_read)
# ============================================================
print("\nBENCHMARK 4: Output File Parsing")
print("-" * 50)

# Create sample output files for parsing benchmark
test_out_dir = base_dir / "parse_test_py"
test_out_dir.mkdir(parents=True, exist_ok=True)

try:
    test_traj = hysplit_trajectory(
        lat=42.83752,
        lon=-80.30364,
        height=50,
        duration=24,
        days=[datetime(2012, 3, 12)],
        daily_hours=[0, 6, 12, 18],
        direction="forward",
        met_type="reanalysis",
        binary_path=binary_path,
        met_dir=str(met_dir),
        exec_dir=str(test_out_dir),
        clean_up=False
    )

    # Find trajectory output folders
    output_folders = list(test_out_dir.glob("traj-*"))

    if output_folders:
        # Benchmark parsing
        parse_times = []
        for i in range(50):
            start = time.perf_counter()
            parsed = trajectory_read(output_folder=str(output_folders[0]))
            end = time.perf_counter()
            parse_times.append(end - start)

        mean_parse_time = np.mean(parse_times)
        print(f"  Mean parse time (4 trajectory files): {mean_parse_time * 1000:.2f} ms")
        if parsed is not None:
            print(f"  Rows parsed: {len(parsed)}")
        add_timing("parsing", "trajectory_read", mean_parse_time)

except Exception as e:
    print(f"  Parsing benchmark error: {e}")

# Cleanup
import shutil
if test_out_dir.exists():
    shutil.rmtree(test_out_dir)

# ============================================================
# BENCHMARK 5: Data Manipulation with pandas
# ============================================================
print("\nBENCHMARK 5: Data Manipulation (pandas)")
print("-" * 50)

if all_trajectories:
    # Combine all trajectories
    combined_start = time.perf_counter()
    combined_traj = pd.concat(all_trajectories, ignore_index=True)
    combined_end = time.perf_counter()
    combine_time = combined_end - combined_start

    print(f"  Combined dataframe rows: {len(combined_traj)}")
    print(f"  Combine time: {combine_time * 1000:.2f} ms")
    add_timing("manipulation", "concat", combine_time)

    # Benchmark common operations
    # Filter
    filter_times = []
    for i in range(100):
        start = time.perf_counter()
        filtered = combined_traj[combined_traj['height'] > 100]
        end = time.perf_counter()
        filter_times.append(end - start)

    print(f"  Mean filter time: {np.mean(filter_times) * 1000:.3f} ms")
    add_timing("manipulation", "filter", np.mean(filter_times))

    # Group by and summarize
    groupby_times = []
    for i in range(100):
        start = time.perf_counter()
        summarized = combined_traj.groupby('run').agg({
            'lat': 'mean',
            'lon': 'mean',
            'height': ['mean', 'max']
        })
        end = time.perf_counter()
        groupby_times.append(end - start)

    print(f"  Mean group_by + summarize time: {np.mean(groupby_times) * 1000:.3f} ms")
    add_timing("manipulation", "group_by_summarize", np.mean(groupby_times))

# ============================================================
# SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("BENCHMARK SUMMARY")
print("=" * 70)
print()

print(f"Total Runs: {run_count}")
print(f"Total Time: {total_trajectory_time:.2f} seconds ({total_trajectory_time / 60:.2f} minutes)")
print()

print("Time Breakdown:")
for result in timing_results:
    print(f"  {result['component']} - {result['operation']}: {result['time_seconds']:.4f} seconds")

# Save results
for result in timing_results:
    result['language'] = 'Python'
    result['total_runs'] = run_count
    result['total_time'] = total_trajectory_time

with open(results_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['component', 'operation', 'time_seconds', 'language', 'total_runs', 'total_time'])
    writer.writeheader()
    writer.writerows(timing_results)

print(f"\nResults saved to: {results_file}")

# Memory usage
print("\nMemory Usage:")
tracemalloc.start()
# Force garbage collection to get accurate memory
import gc
gc.collect()
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"  Current memory: {current / 1024 / 1024:.2f} MB")
print(f"  Peak memory: {peak / 1024 / 1024:.2f} MB")
