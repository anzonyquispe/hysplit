"""Dispersion model implementation for HYSPLIT."""

from __future__ import annotations

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
from hysplit.core.trajectory import get_binary_path, get_os


@dataclass
class EmissionSource:
    """Defines an emission source for dispersion modeling."""

    lat: float
    lon: float
    height: float
    rate: float = 1.0                    # Emission rate (mass/hour)
    area: float = 0.0                    # Source area (m^2)
    heat: float = 0.0                    # Heat release (watts)
    particle_diameter: float = 1.0       # Particle diameter (micrometers)
    particle_density: float = 1.0        # Particle density (g/cm^3)
    particle_shape: float = 1.0          # Shape factor (1.0 = sphere)
    start_time: Optional[datetime] = None
    duration_hours: float = 1.0


@dataclass
class DispersionModel:
    """HYSPLIT Dispersion Model.

    Represents a dispersion model configuration that can be run with HYSPLIT.
    """

    # Time parameters
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: int = 24

    # Model parameters
    direction: str = "forward"
    met_type: str = "reanalysis"
    vert_motion: int = 0
    model_height: int = 20000

    # Emission sources
    sources: List[EmissionSource] = field(default_factory=list)

    # Grid definition
    grid_lat: float = 0.0
    grid_lon: float = 0.0
    grid_spacing_lat: float = 1.0
    grid_spacing_lon: float = 1.0
    grid_span_lat: float = 10.0
    grid_span_lon: float = 10.0
    grid_levels: List[float] = field(default_factory=lambda: [100.0])

    # Output configuration
    sampling_start: int = 0
    sampling_stop: int = 24
    sampling_interval: int = 1

    # Configuration
    config: Optional[HysplitConfig] = None
    ascdata: Optional[AscdataConfig] = None

    # Naming and paths
    disp_name: Optional[str] = None
    binary_path: Optional[Union[str, Path]] = None
    met_dir: Optional[Union[str, Path]] = None
    exec_dir: Optional[Union[str, Path]] = None
    clean_up: bool = True

    # Output
    disp_df: Optional[pd.DataFrame] = field(default=None, repr=False)
    concentration_grid: Optional[np.ndarray] = field(default=None, repr=False)

    def __post_init__(self):
        """Initialize defaults."""
        if self.config is None:
            self.config = set_config()
        if self.ascdata is None:
            self.ascdata = set_ascdata()
        if self.start_time is None:
            self.start_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        if self.end_time is None:
            self.end_time = self.start_time + timedelta(hours=self.duration)

    def add_source(
        self,
        lat: float,
        lon: float,
        height: float,
        rate: float = 1.0,
        area: float = 0.0,
        heat: float = 0.0,
        particle_diameter: float = 1.0,
        particle_density: float = 1.0,
        particle_shape: float = 1.0,
        start_time: Optional[datetime] = None,
        duration_hours: float = 1.0
    ) -> "DispersionModel":
        """Add an emission source. Returns self for method chaining."""
        source = EmissionSource(
            lat=lat,
            lon=lon,
            height=height,
            rate=rate,
            area=area,
            heat=heat,
            particle_diameter=particle_diameter,
            particle_density=particle_density,
            particle_shape=particle_shape,
            start_time=start_time or self.start_time,
            duration_hours=duration_hours
        )
        self.sources.append(source)
        return self

    def add_dispersion_params(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        duration: Optional[int] = None,
        direction: Optional[str] = None,
        met_type: Optional[str] = None,
        vert_motion: Optional[int] = None,
        model_height: Optional[int] = None,
        grid_center: Optional[tuple[float, float]] = None,
        grid_spacing: Optional[tuple[float, float]] = None,
        grid_span: Optional[tuple[float, float]] = None,
        grid_levels: Optional[List[float]] = None
    ) -> "DispersionModel":
        """Add or update dispersion parameters. Returns self for method chaining."""
        if start_time is not None:
            self.start_time = start_time
        if end_time is not None:
            self.end_time = end_time
        if duration is not None:
            self.duration = duration
        if direction is not None:
            self.direction = direction
        if met_type is not None:
            self.met_type = met_type
        if vert_motion is not None:
            self.vert_motion = vert_motion
        if model_height is not None:
            self.model_height = model_height
        if grid_center is not None:
            self.grid_lat, self.grid_lon = grid_center
        if grid_spacing is not None:
            self.grid_spacing_lat, self.grid_spacing_lon = grid_spacing
        if grid_span is not None:
            self.grid_span_lat, self.grid_span_lon = grid_span
        if grid_levels is not None:
            self.grid_levels = grid_levels

        return self

    def _write_control_file(
        self,
        exec_dir: Path,
        met_files: List[str],
        output_filename: str
    ) -> Path:
        """Write HYSPLIT CONTROL file for dispersion."""
        control_path = exec_dir / "CONTROL"

        # Duration direction
        duration = self.duration if self.direction == "forward" else -self.duration

        lines = [
            # Start time: YY MM DD HH
            self.start_time.strftime("%y %m %d %H"),
            # Number of starting locations (sources)
            str(len(self.sources)),
        ]

        # Add source locations
        for source in self.sources:
            lines.append(f"{source.lat:.4f} {source.lon:.4f} {source.height:.1f} {source.rate:.4f} {source.area:.1f} {source.heat:.1f}")

        lines.extend([
            # Total run time (hours)
            str(duration),
            # Vertical motion method
            str(self.vert_motion),
            # Top of model domain (meters)
            str(self.model_height),
            # Number of input meteorological data files
            str(len(met_files)),
        ])

        # Add meteorological file paths
        met_dir = self.met_dir or exec_dir
        for met_file in met_files:
            lines.append(str(met_dir) + "/")
            lines.append(met_file)

        # Number of pollutant species
        lines.append("1")
        # Pollutant identification
        lines.append("PART")
        # Emission rate (per hour)
        lines.append("1.0")
        # Hours of emission
        lines.append(str(int(self.duration)))
        # Release start time (relative to simulation start)
        lines.append("00 00 00 00 00")

        # Number of concentration grids
        lines.append("1")
        # Grid center
        lines.append(f"{self.grid_lat:.4f} {self.grid_lon:.4f}")
        # Grid spacing
        lines.append(f"{self.grid_spacing_lat:.4f} {self.grid_spacing_lon:.4f}")
        # Grid span
        lines.append(f"{self.grid_span_lat:.4f} {self.grid_span_lon:.4f}")

        # Output directory and filename
        lines.append(str(exec_dir) + "/")
        lines.append(output_filename)

        # Number of vertical levels
        lines.append(str(len(self.grid_levels)))
        # Vertical levels
        for level in self.grid_levels:
            lines.append(f"{level:.1f}")

        # Sampling start, stop, interval
        lines.append(f"{self.start_time.strftime('%y %m %d %H')} 00")
        lines.append(f"{self.end_time.strftime('%y %m %d %H')} 00")
        lines.append(f"00 {self.sampling_interval:02d} 00")

        # Deposition
        lines.append("1")  # Number of depositing pollutants
        lines.append("0.0 0.0 0.0")  # Particle diameter, density, shape
        lines.append("0.0 0.0 0.0 0.0 0.0")  # Deposition velocities
        lines.append("0.0 0.0 0.0")  # Wet removal

        with open(control_path, "w") as f:
            f.write("\n".join(lines) + "\n")

        return control_path

    def run(self) -> "DispersionModel":
        """Execute the dispersion model. Returns self for method chaining."""
        from hysplit.met import download_met_files
        from hysplit.io import dispersion_read

        if not self.sources:
            raise ValueError("No emission sources defined. Use add_source() first.")

        # Set up directories
        exec_dir = Path(self.exec_dir) if self.exec_dir else Path(tempfile.mkdtemp())
        met_dir = Path(self.met_dir) if self.met_dir else exec_dir

        exec_dir.mkdir(parents=True, exist_ok=True)
        met_dir.mkdir(parents=True, exist_ok=True)

        # Set binary path
        if self.binary_path:
            binary_path = Path(self.binary_path)
        else:
            binary_path = get_binary_path("hycs_std")

        # Write configuration files
        self.config.to_file(exec_dir)
        self.ascdata.to_file(exec_dir)

        # Calculate days needed for meteorological data
        days = []
        current = self.start_time
        while current <= self.end_time:
            days.append(current)
            current += timedelta(days=1)

        # Download meteorological files
        met_files = download_met_files(
            met_type=self.met_type,
            days=days,
            duration=self.duration,
            direction=self.direction,
            met_dir=met_dir
        )

        output_filename = f"cdump-{self.disp_name or 'default'}"

        # Write CONTROL file
        self._write_control_file(
            exec_dir=exec_dir,
            met_files=met_files,
            output_filename=output_filename
        )

        # Execute HYSPLIT dispersion model
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

        # Read output
        output_path = exec_dir / output_filename
        pardump_path = exec_dir / "PARDUMP"

        if pardump_path.exists():
            self.disp_df = dispersion_read(pardump_path)

        # Clean up if requested
        if self.clean_up and self.exec_dir is None:
            shutil.rmtree(exec_dir, ignore_errors=True)

        return self

    def get_output(self) -> Optional[pd.DataFrame]:
        """Get the dispersion output DataFrame."""
        return self.disp_df

    def plot(self, **kwargs):
        """Plot the dispersion results."""
        from hysplit.viz import dispersion_plot
        return dispersion_plot(self.disp_df, **kwargs)


def create_dispersion_model(
    disp_name: Optional[str] = None,
    start_time: Optional[datetime] = None
) -> DispersionModel:
    """Create a new dispersion model for method chaining.

    Example:
        model = (
            create_dispersion_model()
            .add_source(lat=40.0, lon=-75.0, height=10.0, rate=100.0)
            .add_dispersion_params(duration=48)
            .run()
        )
    """
    return DispersionModel(disp_name=disp_name, start_time=start_time)


def hysplit_dispersion(
    sources: Optional[List[dict]] = None,
    start_time: Optional[datetime] = None,
    duration: int = 24,
    direction: str = "forward",
    met_type: str = "reanalysis",
    vert_motion: int = 0,
    model_height: int = 20000,
    grid_center: tuple[float, float] = (0.0, 0.0),
    grid_spacing: tuple[float, float] = (1.0, 1.0),
    grid_span: tuple[float, float] = (10.0, 10.0),
    grid_levels: Optional[List[float]] = None,
    config: Optional[HysplitConfig] = None,
    ascdata: Optional[AscdataConfig] = None,
    disp_name: Optional[str] = None,
    binary_path: Optional[str] = None,
    met_dir: Optional[str] = None,
    exec_dir: Optional[str] = None,
    clean_up: bool = True
) -> pd.DataFrame:
    """Execute HYSPLIT dispersion model.

    Args:
        sources: List of source dictionaries with keys: lat, lon, height, rate, etc.
        start_time: Simulation start time
        duration: Model run duration (hours)
        direction: "forward" or "backward"
        met_type: Meteorological data type
        vert_motion: Vertical motion method (0-8)
        model_height: Upper model domain (meters)
        grid_center: Center of concentration grid (lat, lon)
        grid_spacing: Grid spacing (lat, lon)
        grid_span: Grid span (lat, lon)
        grid_levels: Vertical levels for concentration output
        config: Optional HysplitConfig object
        ascdata: Optional AscdataConfig object
        disp_name: Optional descriptive name for output
        binary_path: Optional path to HYSPLIT binary
        met_dir: Directory for meteorological files
        exec_dir: Working directory for model execution
        clean_up: Remove temporary files after completion

    Returns:
        DataFrame with particle positions or concentration data
    """
    if start_time is None:
        start_time = datetime.now().replace(minute=0, second=0, microsecond=0)

    if grid_levels is None:
        grid_levels = [100.0]

    model = DispersionModel(
        start_time=start_time,
        duration=duration,
        direction=direction,
        met_type=met_type,
        vert_motion=vert_motion,
        model_height=model_height,
        grid_lat=grid_center[0],
        grid_lon=grid_center[1],
        grid_spacing_lat=grid_spacing[0],
        grid_spacing_lon=grid_spacing[1],
        grid_span_lat=grid_span[0],
        grid_span_lon=grid_span[1],
        grid_levels=grid_levels,
        config=config,
        ascdata=ascdata,
        disp_name=disp_name,
        binary_path=binary_path,
        met_dir=met_dir,
        exec_dir=exec_dir,
        clean_up=clean_up
    )

    # Add sources
    if sources:
        for src in sources:
            model.add_source(**src)

    model.run()
    return model.get_output()
