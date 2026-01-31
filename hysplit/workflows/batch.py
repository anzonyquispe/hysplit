"""
Batch processing utilities for cluster computing.

This module provides tools for running large numbers of HYSPLIT
model runs efficiently on HPC clusters using job arrays or
parallel execution.

Usage:
    # Create batch configuration
    from hysplit.workflows import create_batch_config, run_batch_trajectories

    batch_config = create_batch_config(
        locations=[
            {"lat": 42.83, "lon": -80.30, "height": 50},
            {"lat": 43.45, "lon": -79.70, "height": 100},
        ],
        dates=["2024-01-01", "2024-01-02", "2024-01-03"],
        daily_hours=[0, 6, 12, 18],
        duration=24,
        direction="backward"
    )

    # Save for SLURM job array
    batch_config.to_json("batch_config.json")

    # Or run locally with multiprocessing
    results = run_batch_trajectories(batch_config, n_workers=4)
"""

from __future__ import annotations

import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union, Dict, Any, Callable
import itertools

import pandas as pd


@dataclass
class BatchConfig:
    """Configuration for batch HYSPLIT runs."""

    # Run specifications (each combination creates a job)
    locations: List[Dict[str, float]]  # [{"lat": x, "lon": y, "height": z}, ...]
    dates: List[str]                    # ["2024-01-01", "2024-01-02", ...]
    daily_hours: List[int]              # [0, 6, 12, 18]

    # Model parameters (shared across all runs)
    duration: int = 24
    direction: str = "forward"
    met_type: str = "reanalysis"
    vert_motion: int = 0
    model_height: int = 20000
    extended_met: bool = False

    # Paths
    met_dir: Optional[str] = None
    output_dir: Optional[str] = None
    binary_path: Optional[str] = None

    # Batch info
    batch_name: str = "batch"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def total_runs(self) -> int:
        """Calculate total number of model runs."""
        return len(self.locations) * len(self.dates) * len(self.daily_hours)

    def get_run_params(self, run_index: int) -> Dict[str, Any]:
        """Get parameters for a specific run index (for job arrays)."""
        n_locations = len(self.locations)
        n_dates = len(self.dates)
        n_hours = len(self.daily_hours)

        # Decode index into (location_idx, date_idx, hour_idx)
        location_idx = run_index // (n_dates * n_hours)
        remainder = run_index % (n_dates * n_hours)
        date_idx = remainder // n_hours
        hour_idx = remainder % n_hours

        location = self.locations[location_idx]
        date = self.dates[date_idx]
        hour = self.daily_hours[hour_idx]

        return {
            "run_index": run_index,
            "lat": location["lat"],
            "lon": location["lon"],
            "height": location["height"],
            "date": date,
            "hour": hour,
            "duration": self.duration,
            "direction": self.direction,
            "met_type": self.met_type,
            "vert_motion": self.vert_motion,
            "model_height": self.model_height,
            "extended_met": self.extended_met,
            "met_dir": self.met_dir,
            "binary_path": self.binary_path,
        }

    def iter_runs(self):
        """Iterate over all run parameter combinations."""
        for i in range(self.total_runs()):
            yield self.get_run_params(i)

    def to_json(self, filepath: Union[str, Path]) -> Path:
        """Save batch configuration to JSON."""
        filepath = Path(filepath)
        with open(filepath, "w") as f:
            json.dump(asdict(self), f, indent=2)
        return filepath

    @classmethod
    def from_json(cls, filepath: Union[str, Path]) -> "BatchConfig":
        """Load batch configuration from JSON."""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls(**data)

    def to_slurm_array(self, script_path: Union[str, Path], python_script: str) -> str:
        """Generate a SLURM job array script."""
        total = self.total_runs()
        script = f"""#!/bin/bash
#SBATCH --job-name={self.batch_name}
#SBATCH --array=0-{total - 1}
#SBATCH --output=logs/{self.batch_name}_%A_%a.out
#SBATCH --error=logs/{self.batch_name}_%A_%a.err
#SBATCH --time=01:00:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1

# Load required modules (adjust for your cluster)
# module load python/3.9

# Run the Python script with the array task ID
python {python_script} --config {script_path} --run-index $SLURM_ARRAY_TASK_ID
"""
        return script


def create_batch_config(
    locations: List[Dict[str, float]],
    dates: List[Union[str, datetime]],
    daily_hours: List[int],
    duration: int = 24,
    direction: str = "forward",
    met_type: str = "reanalysis",
    vert_motion: int = 0,
    model_height: int = 20000,
    extended_met: bool = False,
    met_dir: Optional[str] = None,
    output_dir: Optional[str] = None,
    binary_path: Optional[str] = None,
    batch_name: str = "batch"
) -> BatchConfig:
    """
    Create a batch configuration for multiple HYSPLIT runs.

    Args:
        locations: List of location dictionaries with lat, lon, height
        dates: List of dates (strings or datetime objects)
        daily_hours: List of hours to run each day
        duration: Model duration in hours
        direction: "forward" or "backward"
        met_type: Meteorological data type
        vert_motion: Vertical motion method
        model_height: Upper model domain
        extended_met: Include extended meteorology
        met_dir: Directory containing met files
        output_dir: Directory for output files
        binary_path: Path to HYSPLIT binary
        batch_name: Name for the batch (used in job names)

    Returns:
        BatchConfig object
    """
    # Convert dates to strings
    date_strings = []
    for d in dates:
        if isinstance(d, datetime):
            date_strings.append(d.strftime("%Y-%m-%d"))
        else:
            date_strings.append(d)

    return BatchConfig(
        locations=locations,
        dates=date_strings,
        daily_hours=daily_hours,
        duration=duration,
        direction=direction,
        met_type=met_type,
        vert_motion=vert_motion,
        model_height=model_height,
        extended_met=extended_met,
        met_dir=met_dir,
        output_dir=output_dir,
        binary_path=binary_path,
        batch_name=batch_name
    )


def _run_single_trajectory(params: Dict[str, Any]) -> Dict[str, Any]:
    """Worker function to run a single trajectory."""
    from hysplit.core.trajectory import hysplit_trajectory

    try:
        date = datetime.strptime(params["date"], "%Y-%m-%d")
        date = date.replace(hour=params["hour"])

        result = hysplit_trajectory(
            lat=params["lat"],
            lon=params["lon"],
            height=params["height"],
            duration=params["duration"],
            days=[date],
            daily_hours=[params["hour"]],
            direction=params["direction"],
            met_type=params["met_type"],
            vert_motion=params["vert_motion"],
            model_height=params["model_height"],
            extended_met=params["extended_met"],
            met_dir=params["met_dir"],
            binary_path=params["binary_path"],
            clean_up=True
        )

        return {
            "run_index": params["run_index"],
            "success": True,
            "n_points": len(result) if result is not None else 0,
            "error": None
        }

    except Exception as e:
        return {
            "run_index": params["run_index"],
            "success": False,
            "n_points": 0,
            "error": str(e)
        }


def run_batch_trajectories(
    config: BatchConfig,
    n_workers: int = 4,
    progress_callback: Optional[Callable] = None
) -> pd.DataFrame:
    """
    Run batch trajectories using multiprocessing.

    Args:
        config: BatchConfig object
        n_workers: Number of parallel workers
        progress_callback: Optional callback function(completed, total)

    Returns:
        DataFrame with combined results from all runs
    """
    total_runs = config.total_runs()
    print(f"Running {total_runs} trajectories with {n_workers} workers")

    all_params = list(config.iter_runs())
    results = []

    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = {executor.submit(_run_single_trajectory, p): p for p in all_params}

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            if progress_callback:
                progress_callback(completed, total_runs)
            else:
                if completed % 10 == 0:
                    print(f"Progress: {completed}/{total_runs}")

    # Summarize results
    df = pd.DataFrame(results)
    success_rate = df["success"].sum() / len(df) * 100
    print(f"Completed: {len(df)} runs, {success_rate:.1f}% success rate")

    return df


def run_batch_dispersion(
    config: BatchConfig,
    sources: List[Dict],
    n_workers: int = 4
) -> pd.DataFrame:
    """
    Run batch dispersion models using multiprocessing.

    Args:
        config: BatchConfig object (uses dates and met settings)
        sources: List of source dictionaries
        n_workers: Number of parallel workers

    Returns:
        DataFrame with combined results
    """
    # Similar implementation to run_batch_trajectories
    # but for dispersion models
    raise NotImplementedError("Batch dispersion not yet implemented")


# CLI entry point for SLURM job arrays
def main():
    """CLI entry point for running individual batch jobs."""
    import argparse

    parser = argparse.ArgumentParser(description="Run a single trajectory from a batch config")
    parser.add_argument("--config", required=True, help="Path to batch config JSON")
    parser.add_argument("--run-index", type=int, required=True, help="Index of run to execute")
    parser.add_argument("--output-dir", help="Override output directory")

    args = parser.parse_args()

    # Load config
    config = BatchConfig.from_json(args.config)

    # Get params for this run
    params = config.get_run_params(args.run_index)

    # Run single trajectory
    result = _run_single_trajectory(params)

    print(f"Run {args.run_index}: {'SUCCESS' if result['success'] else 'FAILED'}")
    if result["error"]:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
