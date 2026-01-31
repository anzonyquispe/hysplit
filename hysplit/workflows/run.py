"""
Run phase utilities for cluster computing workflows.

This module handles running HYSPLIT models offline using pre-downloaded
meteorological data. No internet connection is required.

Usage:
    # On a cluster without internet access:
    from hysplit.workflows import load_met_manifest, run_trajectory_offline

    # Load manifest to get met data info
    manifest = load_met_manifest("/shared/met_data/manifest_jan2024.json")

    # Run trajectory model offline
    results = run_trajectory_offline(
        lat=42.83752,
        lon=-80.30364,
        height=50,
        duration=24,
        days=["2024-01-15"],
        met_manifest=manifest,
        binary_path="/path/to/hyts_std"
    )
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

import pandas as pd

from hysplit.core.config import HysplitConfig, AscdataConfig, set_config, set_ascdata
from hysplit.core.trajectory import TrajectoryModel
from hysplit.core.dispersion import DispersionModel
from hysplit.io.readers import trajectory_read, dispersion_read


def load_met_manifest(manifest_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load a meteorological data manifest from a JSON file.

    Args:
        manifest_path: Path to the manifest JSON file

    Returns:
        Manifest dictionary
    """
    manifest_path = Path(manifest_path)
    with open(manifest_path, "r") as f:
        return json.load(f)


def _get_met_files_for_dates(
    manifest: Dict[str, Any],
    days: List[datetime],
    duration: int,
    direction: str,
    met_dir: Optional[Path] = None
) -> List[str]:
    """
    Get list of meteorological files needed for the specified dates.

    Args:
        manifest: Loaded manifest dictionary
        days: List of model run days
        duration: Model duration in hours
        direction: "forward" or "backward"
        met_dir: Override met directory

    Returns:
        List of meteorological filenames
    """
    if met_dir is None:
        met_dir = Path(manifest["output_dir"])

    # Get all available files from manifest
    available_files = {f["filename"] for f in manifest["files"]}

    # Just return all available files for now
    # A more sophisticated version would filter based on dates
    return sorted(available_files)


def run_trajectory_offline(
    lat: float,
    lon: float,
    height: float,
    duration: int,
    days: List[Union[str, datetime]],
    met_manifest: Dict[str, Any],
    daily_hours: Union[int, List[int]] = 0,
    direction: str = "forward",
    vert_motion: int = 0,
    model_height: int = 20000,
    extended_met: bool = False,
    config: Optional[HysplitConfig] = None,
    ascdata: Optional[AscdataConfig] = None,
    binary_path: Optional[Union[str, Path]] = None,
    met_dir: Optional[Union[str, Path]] = None,
    exec_dir: Optional[Union[str, Path]] = None,
    clean_up: bool = True,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Run trajectory model offline using pre-downloaded meteorological data.

    This function is designed for cluster computing environments where
    internet access is not available. It uses meteorological data that
    was previously downloaded using download_met_data().

    Args:
        lat: Starting latitude
        lon: Starting longitude
        height: Starting height (meters AGL)
        duration: Model duration (hours)
        days: List of dates to run
        met_manifest: Manifest dictionary from load_met_manifest()
        daily_hours: Hour(s) of day to start runs
        direction: "forward" or "backward"
        vert_motion: Vertical motion method (0-8)
        model_height: Upper model domain (meters)
        extended_met: Include extended meteorology output
        config: Optional HysplitConfig
        ascdata: Optional AscdataConfig
        binary_path: Path to HYSPLIT binary
        met_dir: Override directory for met files (default: from manifest)
        exec_dir: Working directory for model
        clean_up: Remove temporary files after run
        verbose: Print progress information

    Returns:
        DataFrame with trajectory results
    """
    # Parse days
    parsed_days = []
    for day in days:
        if isinstance(day, str):
            parsed_days.append(datetime.strptime(day, "%Y-%m-%d"))
        else:
            parsed_days.append(day)

    # Determine met directory
    if met_dir is None:
        met_dir = Path(met_manifest["output_dir"])
    else:
        met_dir = Path(met_dir)

    # Verify met_type matches
    expected_met_type = met_manifest["met_type"]
    if verbose:
        print(f"Using {expected_met_type} meteorological data from {met_dir}")

    # Get list of met files
    met_files = _get_met_files_for_dates(
        manifest=met_manifest,
        days=parsed_days,
        duration=duration,
        direction=direction,
        met_dir=met_dir
    )

    if verbose:
        print(f"Using {len(met_files)} meteorological files")

    # Create trajectory model with pre-downloaded met files
    model = TrajectoryModel(
        lat=lat,
        lon=lon,
        height=height,
        duration=duration,
        days=parsed_days,
        daily_hours=daily_hours if isinstance(daily_hours, list) else [daily_hours],
        direction=direction,
        met_type=expected_met_type,
        vert_motion=vert_motion,
        model_height=model_height,
        extended_met=extended_met,
        config=config or set_config(),
        ascdata=ascdata or set_ascdata(),
        binary_path=binary_path,
        met_dir=str(met_dir),
        exec_dir=exec_dir,
        clean_up=clean_up
    )

    # Run the model (met files already exist, so no download will occur)
    model.run()

    return model.get_output()


def run_dispersion_offline(
    sources: List[Dict],
    start_time: Union[str, datetime],
    duration: int,
    met_manifest: Dict[str, Any],
    direction: str = "forward",
    vert_motion: int = 0,
    model_height: int = 20000,
    grid_center: tuple = (0.0, 0.0),
    grid_spacing: tuple = (1.0, 1.0),
    grid_span: tuple = (10.0, 10.0),
    grid_levels: Optional[List[float]] = None,
    config: Optional[HysplitConfig] = None,
    ascdata: Optional[AscdataConfig] = None,
    binary_path: Optional[Union[str, Path]] = None,
    met_dir: Optional[Union[str, Path]] = None,
    exec_dir: Optional[Union[str, Path]] = None,
    clean_up: bool = True,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Run dispersion model offline using pre-downloaded meteorological data.

    Args:
        sources: List of source dictionaries with lat, lon, height, rate, etc.
        start_time: Model start time
        duration: Model duration (hours)
        met_manifest: Manifest dictionary from load_met_manifest()
        direction: "forward" or "backward"
        vert_motion: Vertical motion method
        model_height: Upper model domain
        grid_center: Center of concentration grid (lat, lon)
        grid_spacing: Grid spacing (lat, lon)
        grid_span: Grid span (lat, lon)
        grid_levels: Vertical levels
        config: Optional HysplitConfig
        ascdata: Optional AscdataConfig
        binary_path: Path to HYSPLIT binary
        met_dir: Override directory for met files
        exec_dir: Working directory
        clean_up: Remove temporary files
        verbose: Print progress

    Returns:
        DataFrame with dispersion results
    """
    # Parse start_time
    if isinstance(start_time, str):
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M")

    # Determine met directory
    if met_dir is None:
        met_dir = Path(met_manifest["output_dir"])
    else:
        met_dir = Path(met_dir)

    expected_met_type = met_manifest["met_type"]
    if verbose:
        print(f"Using {expected_met_type} meteorological data from {met_dir}")

    # Create dispersion model
    model = DispersionModel(
        start_time=start_time,
        duration=duration,
        direction=direction,
        met_type=expected_met_type,
        vert_motion=vert_motion,
        model_height=model_height,
        grid_lat=grid_center[0],
        grid_lon=grid_center[1],
        grid_spacing_lat=grid_spacing[0],
        grid_spacing_lon=grid_spacing[1],
        grid_span_lat=grid_span[0],
        grid_span_lon=grid_span[1],
        grid_levels=grid_levels or [100.0],
        config=config or set_config(),
        ascdata=ascdata or set_ascdata(),
        binary_path=binary_path,
        met_dir=str(met_dir),
        exec_dir=exec_dir,
        clean_up=clean_up
    )

    # Add sources
    for src in sources:
        model.add_source(**src)

    # Run the model
    model.run()

    return model.get_output()
