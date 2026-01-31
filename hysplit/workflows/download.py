"""
Download phase utilities for cluster computing workflows.

This module handles downloading meteorological data and creating manifests
that can be used later for offline model runs on clusters without internet.

Usage:
    # On a machine with internet access:
    from hysplit.workflows import download_met_data, create_met_manifest

    manifest = download_met_data(
        met_type="gdas1",
        start_date="2024-01-01",
        end_date="2024-01-31",
        output_dir="/shared/met_data/gdas1_jan2024"
    )

    # Save manifest for cluster use
    create_met_manifest(manifest, "/shared/met_data/manifest_jan2024.json")

    # Transfer output_dir to cluster, then use run_trajectory_offline()
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

from hysplit.met.downloaders import (
    get_met_gdas1,
    get_met_gdas0p5,
    get_met_gfs0p25,
    get_met_reanalysis,
    get_met_narr,
    get_met_nam12,
    get_met_era5,
    get_met_hrrr,
)


def _parse_date(date_str: Union[str, datetime]) -> datetime:
    """Parse date string to datetime."""
    if isinstance(date_str, datetime):
        return date_str
    return datetime.strptime(date_str, "%Y-%m-%d")


def _compute_file_hash(filepath: Path) -> str:
    """Compute MD5 hash of a file for integrity verification."""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def download_met_data(
    met_type: str,
    start_date: Union[str, datetime],
    end_date: Union[str, datetime],
    output_dir: Union[str, Path],
    buffer_days: int = 2,
    parallel_downloads: int = 4,
    compute_checksums: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Download meteorological data for a date range.

    This function is meant to be run on a machine with internet access.
    It downloads all necessary met files and creates a manifest that can
    be used for offline runs on a cluster.

    Args:
        met_type: Type of meteorological data (gdas1, reanalysis, etc.)
        start_date: Start date for data range
        end_date: End date for data range
        output_dir: Directory to store downloaded files
        buffer_days: Extra days to download before/after range (for model duration)
        parallel_downloads: Number of parallel download threads
        compute_checksums: Whether to compute MD5 checksums for verification
        verbose: Print progress information

    Returns:
        Dictionary manifest with download information
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Add buffer days
    buffered_start = start_date - timedelta(days=buffer_days)
    buffered_end = end_date + timedelta(days=buffer_days)

    # Generate list of days
    days = []
    current = buffered_start
    while current <= buffered_end:
        days.append(current)
        current += timedelta(days=1)

    if verbose:
        print(f"Downloading {met_type} data from {buffered_start.date()} to {buffered_end.date()}")
        print(f"Output directory: {output_dir}")
        print(f"Number of days: {len(days)}")

    # Select downloader
    downloaders = {
        "gdas1": get_met_gdas1,
        "gdas0.5": get_met_gdas0p5,
        "gfs0.25": get_met_gfs0p25,
        "reanalysis": get_met_reanalysis,
        "narr": get_met_narr,
        "nam12": get_met_nam12,
        "era5": get_met_era5,
        "hrrr": get_met_hrrr,
    }

    if met_type not in downloaders:
        raise ValueError(f"Unknown met_type: {met_type}")

    downloader = downloaders[met_type]

    # Download files (using forward direction to get maximum date coverage)
    downloaded_files = downloader(
        days=days,
        duration=24,  # Dummy duration, we want all files in range
        direction="forward",
        path_met_files=output_dir,
        parallel_downloads=parallel_downloads
    )

    if verbose:
        print(f"Downloaded {len(downloaded_files)} files")

    # Build manifest
    manifest = {
        "met_type": met_type,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "buffered_start": buffered_start.isoformat(),
        "buffered_end": buffered_end.isoformat(),
        "buffer_days": buffer_days,
        "output_dir": str(output_dir.absolute()),
        "download_timestamp": datetime.now().isoformat(),
        "files": []
    }

    # Add file information
    for filename in downloaded_files:
        filepath = output_dir / filename
        if filepath.exists():
            file_info = {
                "filename": filename,
                "size_bytes": filepath.stat().st_size,
            }
            if compute_checksums:
                file_info["md5"] = _compute_file_hash(filepath)
                if verbose:
                    print(f"  Computed checksum for {filename}")
            manifest["files"].append(file_info)

    if verbose:
        total_size = sum(f["size_bytes"] for f in manifest["files"])
        print(f"Total download size: {total_size / (1024**3):.2f} GB")

    return manifest


def create_met_manifest(
    manifest: Dict[str, Any],
    output_path: Union[str, Path]
) -> Path:
    """
    Save a meteorological data manifest to a JSON file.

    Args:
        manifest: Manifest dictionary from download_met_data()
        output_path: Path to save the manifest JSON file

    Returns:
        Path to the saved manifest file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return output_path


def validate_met_data(
    manifest_path: Union[str, Path],
    met_dir: Optional[Union[str, Path]] = None,
    check_checksums: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Validate that all meteorological files are present and intact.

    This is useful to run on the cluster before starting model runs
    to ensure all required data was transferred correctly.

    Args:
        manifest_path: Path to the manifest JSON file
        met_dir: Override directory to check (default: uses manifest path)
        check_checksums: Whether to verify MD5 checksums
        verbose: Print validation progress

    Returns:
        Dictionary with validation results
    """
    manifest_path = Path(manifest_path)

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    if met_dir is None:
        met_dir = Path(manifest["output_dir"])
    else:
        met_dir = Path(met_dir)

    results = {
        "valid": True,
        "met_type": manifest["met_type"],
        "met_dir": str(met_dir),
        "total_files": len(manifest["files"]),
        "missing_files": [],
        "corrupt_files": [],
        "size_mismatch": [],
    }

    if verbose:
        print(f"Validating {len(manifest['files'])} files in {met_dir}")

    for file_info in manifest["files"]:
        filename = file_info["filename"]
        filepath = met_dir / filename

        # Check existence
        if not filepath.exists():
            results["missing_files"].append(filename)
            results["valid"] = False
            if verbose:
                print(f"  MISSING: {filename}")
            continue

        # Check size
        actual_size = filepath.stat().st_size
        expected_size = file_info["size_bytes"]
        if actual_size != expected_size:
            results["size_mismatch"].append({
                "filename": filename,
                "expected": expected_size,
                "actual": actual_size
            })
            results["valid"] = False
            if verbose:
                print(f"  SIZE MISMATCH: {filename} (expected {expected_size}, got {actual_size})")

        # Check checksum
        if check_checksums and "md5" in file_info:
            actual_md5 = _compute_file_hash(filepath)
            if actual_md5 != file_info["md5"]:
                results["corrupt_files"].append({
                    "filename": filename,
                    "expected_md5": file_info["md5"],
                    "actual_md5": actual_md5
                })
                results["valid"] = False
                if verbose:
                    print(f"  CORRUPT: {filename}")

    if verbose:
        if results["valid"]:
            print(f"Validation PASSED: All {results['total_files']} files present and valid")
        else:
            print(f"Validation FAILED:")
            print(f"  Missing: {len(results['missing_files'])}")
            print(f"  Corrupt: {len(results['corrupt_files'])}")
            print(f"  Size mismatch: {len(results['size_mismatch'])}")

    return results
