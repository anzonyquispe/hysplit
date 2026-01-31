"""
Workflow utilities for cluster computing scenarios.

This module provides functionality to split HYSPLIT model runs into two phases:
1. Download phase (requires internet) - downloads meteorological data
2. Run phase (offline) - executes HYSPLIT model using pre-downloaded data

This is useful for HPC clusters that don't have internet access.
"""

from hysplit.workflows.download import (
    download_met_data,
    create_met_manifest,
    validate_met_data,
)
from hysplit.workflows.run import (
    run_trajectory_offline,
    run_dispersion_offline,
    load_met_manifest,
)
from hysplit.workflows.batch import (
    create_batch_config,
    run_batch_trajectories,
    run_batch_dispersion,
)

__all__ = [
    # Download phase
    "download_met_data",
    "create_met_manifest",
    "validate_met_data",
    # Run phase
    "run_trajectory_offline",
    "run_dispersion_offline",
    "load_met_manifest",
    # Batch processing
    "create_batch_config",
    "run_batch_trajectories",
    "run_batch_dispersion",
]
