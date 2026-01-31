"""
HySplit - Python interface to HYSPLIT atmospheric transport model.

A Python port of the R splitr package with C++ optimizations for performance.
"""

__version__ = "0.1.0"
__author__ = "Converted from R splitr package"

from hysplit.core.trajectory import TrajectoryModel, hysplit_trajectory, create_trajectory_model
from hysplit.core.dispersion import DispersionModel, hysplit_dispersion, create_dispersion_model
from hysplit.core.config import set_config, set_ascdata
from hysplit.met import (
    get_met_gdas1,
    get_met_gdas0p5,
    get_met_gfs0p25,
    get_met_reanalysis,
    get_met_narr,
    get_met_nam12,
    get_met_era5,
    get_met_hrrr,
)
from hysplit.io import trajectory_read, dispersion_read
from hysplit.viz import trajectory_plot, dispersion_plot

# Workflow utilities for cluster computing
from hysplit.workflows import (
    download_met_data,
    create_met_manifest,
    validate_met_data,
    run_trajectory_offline,
    run_dispersion_offline,
    load_met_manifest,
    create_batch_config,
    run_batch_trajectories,
)

__all__ = [
    # Core models
    "TrajectoryModel",
    "DispersionModel",
    "hysplit_trajectory",
    "hysplit_dispersion",
    "create_trajectory_model",
    "create_dispersion_model",
    # Configuration
    "set_config",
    "set_ascdata",
    # Meteorological data
    "get_met_gdas1",
    "get_met_gdas0p5",
    "get_met_gfs0p25",
    "get_met_reanalysis",
    "get_met_narr",
    "get_met_nam12",
    "get_met_era5",
    "get_met_hrrr",
    # I/O
    "trajectory_read",
    "dispersion_read",
    # Visualization
    "trajectory_plot",
    "dispersion_plot",
    # Workflow utilities (cluster computing)
    "download_met_data",
    "create_met_manifest",
    "validate_met_data",
    "run_trajectory_offline",
    "run_dispersion_offline",
    "load_met_manifest",
    "create_batch_config",
    "run_batch_trajectories",
]
