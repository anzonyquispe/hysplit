"""Configuration management for HYSPLIT models."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Union
import os


@dataclass
class HysplitConfig:
    """HYSPLIT SETUP.CFG configuration.

    Parameters control turbulence, particle dynamics, meteorology output, etc.
    """
    # Advection and turbulence
    tratio: float = 0.75      # Advection stability ratio
    initd: int = 0            # Initial distribution
    kpuff: int = 0            # Horizontal puff dispersion growth (0=linear, 1=empirical)
    khmax: int = 9999         # Maximum duration in hours
    kmixd: int = 0            # Mixed layer depth method (0=input, 1=temp, 2=TKE)
    kmix0: int = 250          # Minimum mixing depth (meters)
    kzmix: int = 0            # Vertical mixing adjustments
    kdef: int = 0             # Horizontal turbulence method (0=vertical, 1=deformation)
    kbls: int = 1             # Boundary layer stability (1=fluxes, 2=wind temp)
    kblt: int = 2             # BL turbulence param (1=Beljaars, 2=Kanthar, 3=TKE)

    # Particle settings
    conage: int = 48          # Particle to/from puff conversion (hours)
    numpar: int = 2500        # Particles released per cycle
    qcycle: float = 0.0       # Optional emission cycling (hours)
    efile: Optional[str] = None  # Temporal emissions file path

    # Turbulent kinetic energy
    tkerd: float = 0.18       # Unstable TKE ratio
    tkern: float = 0.18       # Stable TKE ratio

    # Particle initialization and output
    ninit: int = 1            # Particle init (0=none, 1=once, 2=add, 3=replace)
    ndump: int = 1            # Particle dump frequency (0=none, >0=hours)
    ncycl: int = 1            # PARDUMP output cycle time
    pinpf: str = "PARINIT"    # Particle input filename
    poutf: str = "PARDUMP"    # Particle output filename

    # Model settings
    mgmin: int = 10           # Minimum met subgrid size
    kmsl: int = 0             # Starting height ref (0=AGL, 1=MSL)
    maxpar: int = 10000       # Maximum particles in simulation
    cpack: int = 1            # Binary concentration packing
    cmass: int = 0            # Grid computation (0=concentration, 1=mass)

    # Ensemble factors
    dxf: float = 1.0          # Horizontal x-grid adjustment
    dyf: float = 1.0          # Horizontal y-grid adjustment
    dzf: float = 0.01         # Vertical factor

    # Chemistry
    ichem: int = 0            # Chemistry module (0=none, 1=matrix, 2=conversion, 3=dust)
    maxdim: int = 1           # Max pollutants per particle

    # Splitting/merging
    kspl: int = 1             # Splitting interval (hours)
    krnd: int = 6             # Merge interval (hours)
    frhs: float = 1.0         # Horizontal rounding fraction
    frvs: float = 0.01        # Vertical rounding fraction
    frts: float = 0.10        # Temporal rounding fraction
    frhmax: float = 3.0       # Max horizontal rounding
    splitf: float = 1.0       # Horizontal splitting factor

    # Trajectory meteorology output flags (0=disabled, 1=enabled)
    tm_pres: int = 0          # Pressure
    tm_tpot: int = 0          # Potential temperature
    tm_tamb: int = 0          # Ambient temperature
    tm_rain: int = 0          # Rainfall rate
    tm_mixd: int = 0          # Mixed layer depth
    tm_relh: int = 0          # Relative humidity
    tm_sphu: int = 0          # Specific humidity
    tm_mixr: int = 0          # Mixing rate
    tm_dswf: int = 0          # Downward shortwave flux
    tm_terr: int = 0          # Terrain height

    def enable_extended_met(self) -> "HysplitConfig":
        """Enable all extended meteorology output."""
        self.tm_pres = 1
        self.tm_tpot = 1
        self.tm_tamb = 1
        self.tm_rain = 1
        self.tm_mixd = 1
        self.tm_relh = 1
        self.tm_sphu = 1
        self.tm_mixr = 1
        self.tm_dswf = 1
        self.tm_terr = 1
        return self

    def to_file(self, directory: Union[str, Path]) -> Path:
        """Write SETUP.CFG file to directory."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        filepath = directory / "SETUP.CFG"

        lines = ["&SETUP"]
        for key, value in asdict(self).items():
            if value is None:
                formatted_value = "''"
            elif isinstance(value, str):
                formatted_value = f"'{value}'"
            else:
                formatted_value = str(value)
            lines.append(f"{key} = {formatted_value},")
        lines.append("/")

        with open(filepath, "w") as f:
            f.write("\n".join(lines) + "\n")

        return filepath


@dataclass
class AscdataConfig:
    """HYSPLIT ASCDATA.CFG configuration for terrain/geographic data."""

    lat_ll: float = -90.0           # Lower-left latitude
    lon_ll: float = -180.0          # Lower-left longitude
    lat_spacing: float = 1.0        # Latitude grid spacing
    lon_spacing: float = 1.0        # Longitude grid spacing
    lat_n: int = 180                # Number of latitude points
    lon_n: int = 360                # Number of longitude points
    lu_category: int = 2            # Land use category
    roughness_l: float = 0.2        # Roughness length
    data_dir: str = "'.'"           # Data directory

    def to_file(self, directory: Union[str, Path]) -> Path:
        """Write ASCDATA.CFG file to directory."""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        filepath = directory / "ASCDATA.CFG"

        lines = [
            f"{self.lat_ll}  {self.lon_ll}",
            f"{self.lat_spacing}  {self.lon_spacing}",
            f"{self.lat_n}  {self.lon_n}",
            str(self.lu_category),
            str(self.roughness_l),
            self.data_dir
        ]

        with open(filepath, "w") as f:
            f.write("\n".join(lines) + "\n")

        return filepath


def set_config(**kwargs) -> HysplitConfig:
    """Create a HYSPLIT configuration with custom parameters.

    Returns a HysplitConfig object that can be passed to trajectory or
    dispersion models.

    Example:
        config = set_config(numpar=5000, extended_met=True)
    """
    extended_met = kwargs.pop("extended_met", False)
    config = HysplitConfig(**kwargs)
    if extended_met:
        config.enable_extended_met()
    return config


def set_ascdata(
    lat_lon_ll: tuple[float, float] = (-90.0, -180.0),
    lat_lon_spacing: tuple[float, float] = (1.0, 1.0),
    lat_lon_n: tuple[int, int] = (180, 360),
    lu_category: int = 2,
    roughness_l: float = 0.2,
    data_dir: str = "'.'"
) -> AscdataConfig:
    """Create ASCDATA configuration for terrain/geographic data.

    Args:
        lat_lon_ll: Lower-left corner (lat, lon)
        lat_lon_spacing: Grid spacing (lat, lon)
        lat_lon_n: Number of grid points (lat, lon)
        lu_category: Land use category
        roughness_l: Roughness length
        data_dir: Data directory path

    Returns:
        AscdataConfig object
    """
    return AscdataConfig(
        lat_ll=lat_lon_ll[0],
        lon_ll=lat_lon_ll[1],
        lat_spacing=lat_lon_spacing[0],
        lon_spacing=lat_lon_spacing[1],
        lat_n=lat_lon_n[0],
        lon_n=lat_lon_n[1],
        lu_category=lu_category,
        roughness_l=roughness_l,
        data_dir=data_dir
    )
