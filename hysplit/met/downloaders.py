"""Meteorological data download functions for different data sources."""

from __future__ import annotations

import math
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Union
import logging

# Configure logging
logger = logging.getLogger(__name__)

# NOAA FTP server URLs for different meteorological data
MET_URLS = {
    "gdas1": "ftp://arlftp.arlhq.noaa.gov/archives/gdas1",
    "gdas0.5": "ftp://arlftp.arlhq.noaa.gov/archives/gdas0p5",
    "gfs0.25": "ftp://arlftp.arlhq.noaa.gov/pub/archives/gfs0p25",
    "reanalysis": "ftp://arlftp.arlhq.noaa.gov/archives/reanalysis",
    "narr": "ftp://arlftp.arlhq.noaa.gov/archives/narr",
    "nam12": "ftp://arlftp.arlhq.noaa.gov/archives/nam12",
    "era5": "ftp://arlftp.arlhq.noaa.gov/archives/era5",
    "hrrr": "ftp://arlftp.arlhq.noaa.gov/pub/archives/hrrr",
}

# Month abbreviations
MONTH_ABBR = [
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec"
]


def _download_file(url: str, filepath: Path, timeout: int = 300) -> bool:
    """Download a single file from URL.

    Args:
        url: Source URL
        filepath: Destination path
        timeout: Download timeout in seconds

    Returns:
        True if download successful, False otherwise
    """
    try:
        if filepath.exists():
            logger.info(f"File already exists: {filepath}")
            return True

        logger.info(f"Downloading: {url}")
        urllib.request.urlretrieve(url, filepath)
        logger.info(f"Downloaded: {filepath}")
        return True

    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return False


def _get_date_range(
    days: List[datetime],
    duration: int,
    direction: str
) -> tuple[datetime, datetime]:
    """Get the date range needed for meteorological data.

    Args:
        days: List of run dates
        duration: Model run duration in hours
        direction: "forward" or "backward"

    Returns:
        Tuple of (min_date, max_date)
    """
    if direction == "backward":
        min_date = (min(days) - timedelta(hours=duration)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        max_date = max(days).replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        min_date = min(days).replace(hour=0, minute=0, second=0, microsecond=0)
        max_date = (max(days) + timedelta(hours=duration)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    return min_date, max_date


def get_met_gdas1(
    days: List[datetime],
    duration: int,
    direction: str,
    path_met_files: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download GDAS1 meteorological data files.

    GDAS1 is 1-degree resolution Global Data Assimilation System data.
    Files are organized by week of month.

    Args:
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        path_met_files: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names
    """
    path_met_files = Path(path_met_files)
    path_met_files.mkdir(parents=True, exist_ok=True)

    min_date, max_date = _get_date_range(days, duration, direction)

    # Generate list of required files
    files_needed = set()
    current = min_date
    while current <= max_date:
        month_abbr = MONTH_ABBR[current.month - 1]
        year_short = current.strftime("%y")
        week_num = math.ceil(current.day / 7)
        filename = f"gdas1.{month_abbr}{year_short}.w{week_num}"
        files_needed.add(filename)
        current += timedelta(days=1)

    files_needed = sorted(files_needed)

    # Download files in parallel
    base_url = MET_URLS["gdas1"]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
        futures = {}
        for filename in files_needed:
            url = f"{base_url}/{filename}"
            filepath = path_met_files / filename
            futures[executor.submit(_download_file, url, filepath)] = filename

        for future in as_completed(futures):
            filename = futures[future]
            if future.result():
                downloaded_files.append(filename)

    return sorted(downloaded_files)


def get_met_gdas0p5(
    days: List[datetime],
    duration: int,
    direction: str,
    path_met_files: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download GDAS 0.5-degree resolution data files.

    Args:
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        path_met_files: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names
    """
    path_met_files = Path(path_met_files)
    path_met_files.mkdir(parents=True, exist_ok=True)

    min_date, max_date = _get_date_range(days, duration, direction)

    files_needed = set()
    current = min_date
    while current <= max_date:
        # GDAS 0.5 uses format: gdas0p5.YYYYMMDD.wWW
        filename = f"gdas0p5.{current.strftime('%Y%m')}.w{math.ceil(current.day / 7)}"
        files_needed.add(filename)
        current += timedelta(days=1)

    files_needed = sorted(files_needed)
    base_url = MET_URLS["gdas0.5"]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
        futures = {}
        for filename in files_needed:
            url = f"{base_url}/{filename}"
            filepath = path_met_files / filename
            futures[executor.submit(_download_file, url, filepath)] = filename

        for future in as_completed(futures):
            filename = futures[future]
            if future.result():
                downloaded_files.append(filename)

    return sorted(downloaded_files)


def get_met_gfs0p25(
    days: List[datetime],
    duration: int,
    direction: str,
    path_met_files: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download GFS 0.25-degree resolution forecast data.

    Args:
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        path_met_files: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names
    """
    path_met_files = Path(path_met_files)
    path_met_files.mkdir(parents=True, exist_ok=True)

    min_date, max_date = _get_date_range(days, duration, direction)

    files_needed = set()
    current = min_date
    while current <= max_date:
        # GFS 0.25 uses daily files
        filename = f"gfs0p25.{current.strftime('%Y%m%d')}"
        files_needed.add(filename)
        current += timedelta(days=1)

    files_needed = sorted(files_needed)
    base_url = MET_URLS["gfs0.25"]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
        futures = {}
        for filename in files_needed:
            url = f"{base_url}/{filename}"
            filepath = path_met_files / filename
            futures[executor.submit(_download_file, url, filepath)] = filename

        for future in as_completed(futures):
            filename = futures[future]
            if future.result():
                downloaded_files.append(filename)

    return sorted(downloaded_files)


def get_met_reanalysis(
    days: List[datetime],
    duration: int,
    direction: str,
    path_met_files: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download NCEP/NCAR reanalysis data files.

    Args:
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        path_met_files: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names
    """
    path_met_files = Path(path_met_files)
    path_met_files.mkdir(parents=True, exist_ok=True)

    min_date, max_date = _get_date_range(days, duration, direction)

    files_needed = set()
    current = min_date
    while current <= max_date:
        # Reanalysis uses format: RP{YYYY}{MM}.gbl
        filename = f"RP{current.strftime('%Y%m')}.gbl"
        files_needed.add(filename)
        current += timedelta(days=28)  # Monthly files

    # Make sure we have the months covering our range
    for d in [min_date, max_date]:
        filename = f"RP{d.strftime('%Y%m')}.gbl"
        files_needed.add(filename)

    files_needed = sorted(files_needed)
    base_url = MET_URLS["reanalysis"]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
        futures = {}
        for filename in files_needed:
            url = f"{base_url}/{filename}"
            filepath = path_met_files / filename
            futures[executor.submit(_download_file, url, filepath)] = filename

        for future in as_completed(futures):
            filename = futures[future]
            if future.result():
                downloaded_files.append(filename)

    return sorted(downloaded_files)


def get_met_narr(
    days: List[datetime],
    duration: int,
    direction: str,
    path_met_files: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download North American Regional Reanalysis data files.

    Args:
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        path_met_files: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names
    """
    path_met_files = Path(path_met_files)
    path_met_files.mkdir(parents=True, exist_ok=True)

    min_date, max_date = _get_date_range(days, duration, direction)

    files_needed = set()
    current = min_date
    while current <= max_date:
        # NARR uses format: narr{YYYYMM}
        filename = f"narr{current.strftime('%Y%m')}"
        files_needed.add(filename)
        current += timedelta(days=28)

    for d in [min_date, max_date]:
        filename = f"narr{d.strftime('%Y%m')}"
        files_needed.add(filename)

    files_needed = sorted(files_needed)
    base_url = MET_URLS["narr"]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
        futures = {}
        for filename in files_needed:
            url = f"{base_url}/{filename}"
            filepath = path_met_files / filename
            futures[executor.submit(_download_file, url, filepath)] = filename

        for future in as_completed(futures):
            filename = futures[future]
            if future.result():
                downloaded_files.append(filename)

    return sorted(downloaded_files)


def get_met_nam12(
    days: List[datetime],
    duration: int,
    direction: str,
    path_met_files: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download North American Mesoscale 12-km forecast data.

    Args:
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        path_met_files: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names
    """
    path_met_files = Path(path_met_files)
    path_met_files.mkdir(parents=True, exist_ok=True)

    min_date, max_date = _get_date_range(days, duration, direction)

    files_needed = set()
    current = min_date
    while current <= max_date:
        # NAM12 uses format: nam12_YYYYMMDD
        filename = f"nam12_{current.strftime('%Y%m%d')}"
        files_needed.add(filename)
        current += timedelta(days=1)

    files_needed = sorted(files_needed)
    base_url = MET_URLS["nam12"]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
        futures = {}
        for filename in files_needed:
            url = f"{base_url}/{filename}"
            filepath = path_met_files / filename
            futures[executor.submit(_download_file, url, filepath)] = filename

        for future in as_completed(futures):
            filename = futures[future]
            if future.result():
                downloaded_files.append(filename)

    return sorted(downloaded_files)


def get_met_era5(
    days: List[datetime],
    duration: int,
    direction: str,
    path_met_files: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download ERA5 reanalysis data files.

    Args:
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        path_met_files: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names
    """
    path_met_files = Path(path_met_files)
    path_met_files.mkdir(parents=True, exist_ok=True)

    min_date, max_date = _get_date_range(days, duration, direction)

    files_needed = set()
    current = min_date
    while current <= max_date:
        # ERA5 uses format: ERA5_{YYYY}{MM}.ARL
        filename = f"ERA5_{current.strftime('%Y%m')}.ARL"
        files_needed.add(filename)
        current += timedelta(days=28)

    for d in [min_date, max_date]:
        filename = f"ERA5_{d.strftime('%Y%m')}.ARL"
        files_needed.add(filename)

    files_needed = sorted(files_needed)
    base_url = MET_URLS["era5"]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
        futures = {}
        for filename in files_needed:
            url = f"{base_url}/{filename}"
            filepath = path_met_files / filename
            futures[executor.submit(_download_file, url, filepath)] = filename

        for future in as_completed(futures):
            filename = futures[future]
            if future.result():
                downloaded_files.append(filename)

    return sorted(downloaded_files)


def get_met_hrrr(
    days: List[datetime],
    duration: int,
    direction: str,
    path_met_files: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download High-Resolution Rapid Refresh data files.

    Args:
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        path_met_files: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names
    """
    path_met_files = Path(path_met_files)
    path_met_files.mkdir(parents=True, exist_ok=True)

    min_date, max_date = _get_date_range(days, duration, direction)

    files_needed = set()
    current = min_date
    while current <= max_date:
        # HRRR uses format: hrrr.{YYYYMMDD}.nathrrr
        filename = f"hrrr.{current.strftime('%Y%m%d')}.nathrrr"
        files_needed.add(filename)
        current += timedelta(days=1)

    files_needed = sorted(files_needed)
    base_url = MET_URLS["hrrr"]
    downloaded_files = []

    with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
        futures = {}
        for filename in files_needed:
            url = f"{base_url}/{filename}"
            filepath = path_met_files / filename
            futures[executor.submit(_download_file, url, filepath)] = filename

        for future in as_completed(futures):
            filename = futures[future]
            if future.result():
                downloaded_files.append(filename)

    return sorted(downloaded_files)


def download_met_files(
    met_type: str,
    days: List[datetime],
    duration: int,
    direction: str,
    met_dir: Union[str, Path],
    parallel_downloads: int = 4
) -> List[str]:
    """Download meteorological files based on type.

    This is the main dispatcher function that calls the appropriate
    downloader based on met_type.

    Args:
        met_type: Type of meteorological data
        days: List of dates for model runs
        duration: Model run duration in hours
        direction: "forward" or "backward"
        met_dir: Directory to save met files
        parallel_downloads: Number of parallel download threads

    Returns:
        List of downloaded file names

    Raises:
        ValueError: If met_type is not recognized
    """
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
        valid_types = ", ".join(sorted(downloaders.keys()))
        raise ValueError(
            f"Unknown met_type: '{met_type}'. Valid types are: {valid_types}"
        )

    return downloaders[met_type](
        days=days,
        duration=duration,
        direction=direction,
        path_met_files=met_dir,
        parallel_downloads=parallel_downloads
    )
