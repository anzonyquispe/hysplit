"""Trajectory model implementation for HYSPLIT."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union, List

import pandas as pd
import numpy as np

from hysplit.core.config import HysplitConfig, AscdataConfig, set_config, set_ascdata


def get_os() -> str:
    """Get the operating system type."""
    system = platform.system().lower()
    if system == "darwin":
        return "osx"
    elif system == "windows":
        return "win"
    else:
        return "linux"


def get_binary_path(binary_name: str = "hyts_std") -> Path:
    """Get the path to the HYSPLIT binary for the current platform.

    If the binary is not found in the package, it will look for it in PATH.
    """
    os_type = get_os()

    # Try to find in the package's binaries directory
    pkg_dir = Path(__file__).parent.parent
    binary_dir = pkg_dir / "bin" / os_type

    if os_type == "win":
        binary_name = binary_name + ".exe"

    binary_path = binary_dir / binary_name

    if binary_path.exists():
        return binary_path

    # Try to find in PATH
    which_result = shutil.which(binary_name)
    if which_result:
        return Path(which_result)

    raise FileNotFoundError(
        f"HYSPLIT binary '{binary_name}' not found. "
        "Please install HYSPLIT and ensure it's in your PATH, "
        "or provide a custom binary_path."
    )


def to_short_year(date: datetime) -> str:
    """Convert date to 2-digit year string."""
    return date.strftime("%y")


def to_short_month(date: datetime) -> str:
    """Convert date to 2-digit month string."""
    return date.strftime("%m")


def to_short_day(date: datetime) -> str:
    """Convert date to 2-digit day string."""
    return date.strftime("%d")


@dataclass
class TrajectoryModel:
    """HYSPLIT Trajectory Model.

    Represents a trajectory model configuration that can be run with HYSPLIT.
    Supports method chaining for building complex model configurations.
    """

    # Location parameters
    lat: Union[float, List[float]] = 49.263
    lon: Union[float, List[float]] = -123.250
    height: Union[float, List[float]] = 50.0

    # Time parameters
    duration: int = 24
    days: Optional[List[datetime]] = None
    daily_hours: Union[int, List[int]] = 0

    # Model parameters
    direction: str = "forward"
    met_type: str = "reanalysis"
    vert_motion: int = 0
    model_height: int = 20000
    extended_met: bool = False

    # Configuration
    config: Optional[HysplitConfig] = None
    ascdata: Optional[AscdataConfig] = None

    # Naming and paths
    traj_name: Optional[str] = None
    binary_path: Optional[Union[str, Path]] = None
    met_dir: Optional[Union[str, Path]] = None
    exec_dir: Optional[Union[str, Path]] = None
    clean_up: bool = True

    # Output
    traj_df: Optional[pd.DataFrame] = field(default=None, repr=False)

    def __post_init__(self):
        """Initialize defaults after dataclass creation."""
        if self.config is None:
            self.config = set_config()
        if self.ascdata is None:
            self.ascdata = set_ascdata()
        if self.days is None:
            self.days = [datetime.now()]

        # Convert single values to lists for uniformity
        if isinstance(self.lat, (int, float)):
            self.lat = [float(self.lat)]
        if isinstance(self.lon, (int, float)):
            self.lon = [float(self.lon)]
        if isinstance(self.height, (int, float)):
            self.height = [float(self.height)]
        if isinstance(self.daily_hours, int):
            self.daily_hours = [self.daily_hours]

    def add_trajectory_params(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        height: Optional[float] = None,
        duration: Optional[int] = None,
        days: Optional[List[datetime]] = None,
        daily_hours: Optional[List[int]] = None,
        direction: Optional[str] = None,
        met_type: Optional[str] = None,
        vert_motion: Optional[int] = None,
        model_height: Optional[int] = None,
        extended_met: Optional[bool] = None
    ) -> "TrajectoryModel":
        """Add or update trajectory parameters. Supports method chaining."""
        if lat is not None:
            self.lat = [lat] if isinstance(lat, (int, float)) else lat
        if lon is not None:
            self.lon = [lon] if isinstance(lon, (int, float)) else lon
        if height is not None:
            self.height = [height] if isinstance(height, (int, float)) else height
        if duration is not None:
            self.duration = duration
        if days is not None:
            self.days = days
        if daily_hours is not None:
            self.daily_hours = daily_hours if isinstance(daily_hours, list) else [daily_hours]
        if direction is not None:
            self.direction = direction
        if met_type is not None:
            self.met_type = met_type
        if vert_motion is not None:
            self.vert_motion = vert_motion
        if model_height is not None:
            self.model_height = model_height
        if extended_met is not None:
            self.extended_met = extended_met

        return self

    def _write_control_file(
        self,
        exec_dir: Path,
        start_time: datetime,
        lat: float,
        lon: float,
        height: float,
        met_files: List[str],
        output_filename: str
    ) -> Path:
        """Write HYSPLIT CONTROL file."""
        control_path = exec_dir / "CONTROL"

        # Determine direction sign for duration
        duration = self.duration if self.direction == "forward" else -self.duration

        lines = [
            # Start time: YY MM DD HH
            f"{start_time.strftime('%y %m %d %H')}",
            # Number of starting locations
            "1",
            # Starting location: lat lon height
            f"{lat:.4f} {lon:.4f} {height:.1f}",
            # Total run time (hours)
            str(duration),
            # Vertical motion method
            str(self.vert_motion),
            # Top of model domain (meters)
            str(self.model_height),
            # Number of input meteorological data files
            str(len(met_files)),
        ]

        # Add meteorological file paths
        met_dir = self.met_dir or exec_dir
        for met_file in met_files:
            lines.append(str(met_dir) + "/")
            lines.append(met_file)

        # Output directory and filename
        lines.append(str(exec_dir) + "/")
        lines.append(output_filename)

        with open(control_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        return control_path

    def _get_output_filename(
        self,
        receptor_idx: int,
        start_time: datetime,
        lat: float,
        lon: float,
        height: float
    ) -> str:
        """Generate trajectory output filename."""
        direction_str = "fwd" if self.direction == "forward" else "bwd"
        lat_str = f"{abs(lat):.3f}{'N' if lat >= 0 else 'S'}"
        lon_str = f"{abs(lon):.3f}{'E' if lon >= 0 else 'W'}"

        return (
            f"traj-{self.traj_name or 'default'}-"
            f"{receptor_idx:03d}-"
            f"{direction_str}-"
            f"{start_time.strftime('%Y%m%d%H')}-"
            f"{lat_str}-{lon_str}-"
            f"{height:.0f}m-"
            f"{abs(self.duration):03d}h"
        )

    def run(self) -> "TrajectoryModel":
        """Execute the trajectory model.

        Returns self for method chaining.
        """
        from hysplit.met import download_met_files
        from hysplit.io import trajectory_read

        # Set up directories
        exec_dir = Path(self.exec_dir) if self.exec_dir else Path(tempfile.mkdtemp())
        met_dir = Path(self.met_dir) if self.met_dir else exec_dir

        # Ensure directories exist
        exec_dir.mkdir(parents=True, exist_ok=True)
        met_dir.mkdir(parents=True, exist_ok=True)

        # Set binary path
        if self.binary_path:
            binary_path = Path(self.binary_path)
        else:
            binary_path = get_binary_path("hyts_std")

        # Write configuration files
        if self.extended_met:
            self.config.enable_extended_met()
        self.config.to_file(exec_dir)
        self.ascdata.to_file(exec_dir)

        # Download meteorological files
        met_files = download_met_files(
            met_type=self.met_type,
            days=self.days,
            duration=self.duration,
            direction=self.direction,
            met_dir=met_dir
        )

        # Generate receptor combinations
        receptors = []
        for lat in self.lat:
            for lon in self.lon:
                for height in self.height:
                    receptors.append((lat, lon, height))

        all_trajectories = []
        all_output_files = []

        # Run for each receptor
        for receptor_idx, (lat, lon, height) in enumerate(receptors, 1):
            # Run for each day and hour
            for day in self.days:
                for hour in self.daily_hours:
                    start_time = day.replace(hour=hour, minute=0, second=0, microsecond=0)

                    output_filename = self._get_output_filename(
                        receptor_idx, start_time, lat, lon, height
                    )

                    # Write CONTROL file
                    self._write_control_file(
                        exec_dir=exec_dir,
                        start_time=start_time,
                        lat=lat,
                        lon=lon,
                        height=height,
                        met_files=met_files,
                        output_filename=output_filename
                    )

                    # Execute HYSPLIT
                    result = subprocess.run(
                        [str(binary_path)],
                        cwd=str(exec_dir),
                        capture_output=True,
                        text=True
                    )

                    if result.returncode != 0:
                        print(f"Warning: HYSPLIT returned non-zero exit code: {result.returncode}")
                        if result.stderr:
                            print(f"stderr: {result.stderr}")

                    output_path = exec_dir / output_filename
                    if output_path.exists():
                        all_output_files.append(output_path)

        # Read and combine all trajectory outputs
        if all_output_files:
            traj_dfs = []
            for i, output_file in enumerate(all_output_files):
                df = trajectory_read(output_file)
                if df is not None and not df.empty:
                    df["run"] = i + 1
                    traj_dfs.append(df)

            if traj_dfs:
                self.traj_df = pd.concat(traj_dfs, ignore_index=True)

        # Clean up if requested
        if self.clean_up and self.exec_dir is None:
            shutil.rmtree(exec_dir, ignore_errors=True)

        return self

    def get_output(self) -> Optional[pd.DataFrame]:
        """Get the trajectory output DataFrame."""
        return self.traj_df

    def plot(self, **kwargs):
        """Plot the trajectory results."""
        from hysplit.viz import trajectory_plot
        return trajectory_plot(self.traj_df, **kwargs)


def create_trajectory_model(
    traj_name: Optional[str] = None,
    lat: float = 49.263,
    lon: float = -123.250,
    height: float = 50.0
) -> TrajectoryModel:
    """Create a new trajectory model for method chaining.

    Example:
        model = (
            create_trajectory_model()
            .add_trajectory_params(lat=50.0, lon=-120.0, height=100)
            .add_trajectory_params(duration=48, direction="backward")
            .run()
        )
    """
    return TrajectoryModel(lat=lat, lon=lon, height=height, traj_name=traj_name)


def hysplit_trajectory(
    lat: float = 49.263,
    lon: float = -123.250,
    height: float = 50.0,
    duration: int = 24,
    days: Optional[List[datetime]] = None,
    daily_hours: Union[int, List[int]] = 0,
    direction: str = "forward",
    met_type: str = "reanalysis",
    vert_motion: int = 0,
    model_height: int = 20000,
    extended_met: bool = False,
    config: Optional[HysplitConfig] = None,
    ascdata: Optional[AscdataConfig] = None,
    traj_name: Optional[str] = None,
    binary_path: Optional[str] = None,
    met_dir: Optional[str] = None,
    exec_dir: Optional[str] = None,
    clean_up: bool = True
) -> pd.DataFrame:
    """Execute HYSPLIT trajectory model runs.

    This is the main entry point for running trajectory models. It downloads
    meteorological data, executes the model, and returns results as a DataFrame.

    Args:
        lat: Starting latitude (decimal degrees)
        lon: Starting longitude (decimal degrees)
        height: Starting height (meters above ground level)
        duration: Model run duration (hours)
        days: List of dates to run the model
        daily_hours: Hour(s) of day to initiate runs (0-23)
        direction: "forward" or "backward"
        met_type: Meteorological data type ("reanalysis", "gdas1", "gdas0.5", etc.)
        vert_motion: Vertical motion method (0-8)
        model_height: Upper model domain (meters)
        extended_met: Include extended meteorology in output
        config: Optional HysplitConfig object
        ascdata: Optional AscdataConfig object
        traj_name: Optional descriptive name for output
        binary_path: Optional path to HYSPLIT binary
        met_dir: Directory for meteorological files
        exec_dir: Working directory for model execution
        clean_up: Remove temporary files after completion

    Returns:
        DataFrame with trajectory data

    Example:
        from datetime import datetime, timedelta

        trajectory = hysplit_trajectory(
            lat=50.108,
            lon=-122.942,
            height=100,
            duration=48,
            days=[datetime(2024, 6, 1) + timedelta(days=i) for i in range(3)],
            daily_hours=[0, 6, 12, 18]
        )
    """
    if days is None:
        days = [datetime.now()]

    model = TrajectoryModel(
        lat=lat,
        lon=lon,
        height=height,
        duration=duration,
        days=days,
        daily_hours=daily_hours,
        direction=direction,
        met_type=met_type,
        vert_motion=vert_motion,
        model_height=model_height,
        extended_met=extended_met,
        config=config,
        ascdata=ascdata,
        traj_name=traj_name,
        binary_path=binary_path,
        met_dir=met_dir,
        exec_dir=exec_dir,
        clean_up=clean_up
    )

    model.run()
    return model.get_output()
