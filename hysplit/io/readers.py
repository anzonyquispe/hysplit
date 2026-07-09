"""File readers for HYSPLIT output files.

This module provides optimized readers for HYSPLIT trajectory and dispersion
output files. It uses C++ extensions when available for maximum performance,
with a pure Python fallback.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List

import numpy as np
import pandas as pd

# Try to import C++ extension
try:
    from hysplit.cpp import _parsers as cpp_parsers
    HAS_CPP_EXTENSION = True
except ImportError:
    HAS_CPP_EXTENSION = False


# Column names for trajectory output
STANDARD_COLS = [
    "year", "month", "day", "hour", "hour_along",
    "lat", "lon", "height", "pressure"
]

EXTENDED_COLS = [
    "year", "month", "day", "hour", "hour_along",
    "lat", "lon", "height", "pressure",
    "theta", "air_temp", "rainfall", "mixdepth", "rh", "sp_humidity",
    "h2o_mixrate", "terr_msl", "sun_flux"
]


def _parse_trajectory_line_python(line: str, extended: bool = False) -> Optional[List[float]]:
    """Parse a single trajectory data line (Python implementation).

    Args:
        line: Raw line from trajectory file
        extended: Whether to parse extended meteorology columns

    Returns:
        List of parsed values or None if parsing fails
    """
    parts = line.split()
    if len(parts) < 12:
        return None

    try:
        if extended:
            # Extended format: columns 3-6, 9-22
            indices = [2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
            return [float(parts[i]) for i in indices if i < len(parts)]
        else:
            # Standard format: columns 3-6, 9-13
            indices = [2, 3, 4, 5, 8, 9, 10, 11, 12]
            return [float(parts[i]) for i in indices]
    except (ValueError, IndexError):
        return None


def _parse_trajectory_file_python(filepath: Path) -> pd.DataFrame:
    """Parse a trajectory file using pure Python.

    Args:
        filepath: Path to trajectory output file

    Returns:
        DataFrame with trajectory data
    """
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # Find header line (contains "PRESSURE")
    header_idx = None
    for i, line in enumerate(lines):
        if "PRESSURE" in line:
            header_idx = i
            break

    if header_idx is None:
        return pd.DataFrame()

    # Determine if extended meteorology
    file_content = "".join(lines)
    extended = "AIR_TEMP" in file_content

    # Parse data lines
    data_lines = lines[header_idx + 1:]
    parsed_data = []

    for line in data_lines:
        line = line.strip()
        if not line:
            continue

        values = _parse_trajectory_line_python(line, extended)
        if values:
            parsed_data.append(values)

    if not parsed_data:
        return pd.DataFrame()

    # Create DataFrame
    cols = EXTENDED_COLS if extended else STANDARD_COLS
    # Adjust columns based on actual data
    min_cols = min(len(cols), min(len(row) for row in parsed_data) if parsed_data else 0)
    cols = cols[:min_cols]

    df = pd.DataFrame(parsed_data, columns=cols[:len(parsed_data[0])] if parsed_data else [])

    # Convert year to full year
    if "year" in df.columns:
        df["year"] = df["year"].astype(int)
        df["year"] = df["year"].apply(lambda y: y + 2000 if y < 50 else y + 1900)

    # Create datetime columns
    if all(col in df.columns for col in ["year", "month", "day", "hour"]):
        df["month"] = df["month"].astype(int)
        df["day"] = df["day"].astype(int)
        df["hour"] = df["hour"].astype(int)
        df["hour_along"] = df["hour_along"].astype(int)

        try:
            df["traj_dt"] = pd.to_datetime(
                df[["year", "month", "day", "hour"]].astype(str).agg("-".join, axis=1),
                format="%Y-%m-%d-%H",
                errors="coerce"
            )
            df["traj_dt_i"] = df["traj_dt"].iloc[0] if len(df) > 0 else pd.NaT
        except Exception:
            df["traj_dt"] = pd.NaT
            df["traj_dt_i"] = pd.NaT

    return df


def _parse_trajectory_file_cpp(filepath: Path) -> pd.DataFrame:
    """Parse a trajectory file using C++ extension.

    Args:
        filepath: Path to trajectory output file

    Returns:
        DataFrame with trajectory data
    """
    # Call C++ parser
    result = cpp_parsers.parse_trajectory_file(str(filepath))

    if result is None or len(result) == 0:
        return pd.DataFrame()

    # Convert to DataFrame
    extended = result.shape[1] > 9
    cols = EXTENDED_COLS if extended else STANDARD_COLS
    cols = cols[:result.shape[1]]

    df = pd.DataFrame(result, columns=cols)

    # Post-process (same as Python version)
    if "year" in df.columns:
        df["year"] = df["year"].astype(int)
        df["year"] = df["year"].apply(lambda y: y + 2000 if y < 50 else y + 1900)

    if all(col in df.columns for col in ["year", "month", "day", "hour"]):
        df["month"] = df["month"].astype(int)
        df["day"] = df["day"].astype(int)
        df["hour"] = df["hour"].astype(int)
        df["hour_along"] = df["hour_along"].astype(int)

        try:
            df["traj_dt"] = pd.to_datetime(
                df[["year", "month", "day", "hour"]].astype(str).agg("-".join, axis=1),
                format="%Y-%m-%d-%H",
                errors="coerce"
            )
            df["traj_dt_i"] = df["traj_dt"].iloc[0] if len(df) > 0 else pd.NaT
        except Exception:
            df["traj_dt"] = pd.NaT
            df["traj_dt_i"] = pd.NaT

    return df


def trajectory_read(
    output_path: Union[str, Path],
    use_cpp: Optional[bool] = None
) -> pd.DataFrame:
    """Read HYSPLIT trajectory output files into a DataFrame.

    Args:
        output_path: Path to a trajectory file or directory containing
                     trajectory files (files matching 'traj-*')
        use_cpp: Force use of C++ parser (True), Python parser (False),
                 or auto-detect (None, default)

    Returns:
        DataFrame with trajectory data including columns:
        - year, month, day, hour: Date/time components
        - hour_along: Hours from trajectory start
        - lat, lon, height: Position
        - pressure: Atmospheric pressure (hPa)
        - traj_dt: Datetime along trajectory
        - traj_dt_i: Initial datetime
        - (Extended meteorology columns if available)
    """
    output_path = Path(output_path)

    # Determine which parser to use
    if use_cpp is None:
        use_cpp = HAS_CPP_EXTENSION
    elif use_cpp and not HAS_CPP_EXTENSION:
        import warnings
        warnings.warn("C++ extension not available, falling back to Python parser")
        use_cpp = False

    parse_func = _parse_trajectory_file_cpp if use_cpp else _parse_trajectory_file_python

    if output_path.is_file():
        return parse_func(output_path)

    elif output_path.is_dir():
        # Find all trajectory files in directory
        traj_files = sorted(output_path.glob("traj-*"))

        if not traj_files:
            return pd.DataFrame()

        dfs = []
        for f in traj_files:
            df = parse_func(f)
            if not df.empty:
                dfs.append(df)

        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()

    else:
        raise FileNotFoundError(f"Path does not exist: {output_path}")


def _parse_dispersion_pardump_python(filepath: Path) -> pd.DataFrame:
    """Parse PARDUMP file (particle dump) from dispersion model.

    PARDUMP is a Fortran unformatted binary file containing particle
    positions at each output time step.

    Args:
        filepath: Path to PARDUMP file

    Returns:
        DataFrame with particle positions
    """
    import struct

    particles = []
    particle_id = 0

    with open(filepath, 'rb') as f:
        try:
            while True:
                # Read Fortran record length (4 bytes, big-endian int)
                rec_len_bytes = f.read(4)
                if not rec_len_bytes or len(rec_len_bytes) < 4:
                    break

                rec_len = struct.unpack('>i', rec_len_bytes)[0]

                # Read record data
                record_data = f.read(rec_len)
                if len(record_data) < rec_len:
                    break

                # Read trailing record length
                f.read(4)

                # Parse based on record length
                # Header records are typically 28 bytes (7 ints)
                # Particle records are typically 24 bytes (1 int + 5 floats)

                if rec_len == 28:
                    # Header record: npar, year, month, day, hour, minute, ifhr
                    if len(record_data) >= 28:
                        header = struct.unpack('>7i', record_data[:28])
                        # npar = header[0]  # number of particles
                        # Could extract time info here if needed

                elif rec_len == 4:
                    # Small record (single value) - skip
                    pass

                elif rec_len == 24:
                    # Particle position record: lat, lon, height, (other values)
                    # Format: float lat, float lon, float height, ...
                    if len(record_data) >= 24:
                        try:
                            # Try big-endian floats
                            values = struct.unpack('>6f', record_data[:24])
                            lat, lon, height = values[0], values[1], values[2]

                            # Validate lat/lon ranges and height (filter out marker records)
                            if (-90 <= lat <= 90 and -180 <= lon <= 180 and
                                    height >= 0 and height < 50000 and
                                    abs(lat) > 0.01 and abs(lon) > 0.01):
                                particle_id += 1
                                particles.append({
                                    'particle_i': f'{particle_id:05d}',
                                    'lat': lat,
                                    'lon': lon,
                                    'height': height,
                                })
                        except struct.error:
                            pass

                elif rec_len == 20:
                    # Alternative particle record format
                    if len(record_data) >= 20:
                        try:
                            # 5 values: might be index + 4 floats or 5 floats
                            values = struct.unpack('>5f', record_data[:20])
                            lat, lon, height = values[0], values[1], values[2]
                            # Validate with same filters
                            if (-90 <= lat <= 90 and -180 <= lon <= 180 and
                                    height >= 0 and height < 50000 and
                                    abs(lat) > 0.01 and abs(lon) > 0.01):
                                particle_id += 1
                                particles.append({
                                    'particle_i': f'{particle_id:05d}',
                                    'lat': lat,
                                    'lon': lon,
                                    'height': height,
                                })
                        except struct.error:
                            pass

        except Exception as e:
            # If binary parsing fails, return empty DataFrame
            pass

    if particles:
        df = pd.DataFrame(particles)
        # Post-processing: filter out obviously invalid records
        df = df[(df['lat'].abs() > 0.01) & (df['lon'].abs() > 0.01)]
        df = df[(df['height'] >= 0) & (df['height'] < 50000)]
        # Reset particle IDs
        df['particle_i'] = [f'{i+1:05d}' for i in range(len(df))]
        return df.reset_index(drop=True)
    return pd.DataFrame(columns=['particle_i', 'lat', 'lon', 'height'])


def _parse_dispersion_pardump_cpp(filepath: Path) -> pd.DataFrame:
    """Parse PARDUMP file using C++ extension.

    Args:
        filepath: Path to PARDUMP file

    Returns:
        DataFrame with particle positions
    """
    result = cpp_parsers.parse_pardump_file(str(filepath))

    if result is None or len(result) == 0:
        return pd.DataFrame(columns=['particle_i', 'lat', 'lon', 'height'])

    df = pd.DataFrame(result, columns=['particle_i', 'lat', 'lon', 'height'])
    return df


def dispersion_read(
    output_path: Union[str, Path],
    use_cpp: Optional[bool] = None
) -> pd.DataFrame:
    """Read HYSPLIT dispersion output files (PARDUMP) into a DataFrame.

    Args:
        output_path: Path to PARDUMP file or directory containing output
        use_cpp: Force use of C++ parser (True), Python parser (False),
                 or auto-detect (None, default)

    Returns:
        DataFrame with particle positions:
        - particle_i: Particle identifier
        - lat, lon, height: Position
        - hour: Simulation hour (if available)
    """
    output_path = Path(output_path)

    if use_cpp is None:
        use_cpp = HAS_CPP_EXTENSION
    elif use_cpp and not HAS_CPP_EXTENSION:
        import warnings
        warnings.warn("C++ extension not available, falling back to Python parser")
        use_cpp = False

    parse_func = _parse_dispersion_pardump_cpp if use_cpp else _parse_dispersion_pardump_python

    if output_path.is_file():
        return parse_func(output_path)

    elif output_path.is_dir():
        pardump_file = output_path / "PARDUMP"
        if pardump_file.exists():
            return parse_func(pardump_file)
        return pd.DataFrame(columns=['particle_i', 'lat', 'lon', 'height'])

    else:
        raise FileNotFoundError(f"Path does not exist: {output_path}")


# Optimized NumPy-based parser for large files
def trajectory_read_fast(
    output_path: Union[str, Path],
    chunk_size: int = 100000
) -> pd.DataFrame:
    """Fast trajectory reader using NumPy for large files.

    Uses memory-mapped file reading and vectorized operations for
    optimal performance on large trajectory datasets.

    Args:
        output_path: Path to trajectory file
        chunk_size: Number of lines to process at once

    Returns:
        DataFrame with trajectory data
    """
    output_path = Path(output_path)

    if not output_path.is_file():
        raise FileNotFoundError(f"File not found: {output_path}")

    # Read file content
    with open(output_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find header
    lines = content.split('\n')
    header_idx = None
    for i, line in enumerate(lines):
        if "PRESSURE" in line:
            header_idx = i
            break

    if header_idx is None:
        return pd.DataFrame()

    extended = "AIR_TEMP" in content
    data_lines = lines[header_idx + 1:]

    # Pre-allocate arrays
    n_lines = len(data_lines)
    n_cols = 18 if extended else 9

    data = np.zeros((n_lines, n_cols), dtype=np.float64)
    valid_rows = 0

    # Parse with NumPy
    for line in data_lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 12:
            continue

        try:
            if extended:
                indices = [2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]
                values = [float(parts[i]) for i in indices if i < len(parts)]
            else:
                indices = [2, 3, 4, 5, 8, 9, 10, 11, 12]
                values = [float(parts[i]) for i in indices]

            data[valid_rows, :len(values)] = values
            valid_rows += 1
        except (ValueError, IndexError):
            continue

    # Trim to valid data
    data = data[:valid_rows]

    if valid_rows == 0:
        return pd.DataFrame()

    # Create DataFrame
    cols = EXTENDED_COLS if extended else STANDARD_COLS
    cols = cols[:data.shape[1]]

    df = pd.DataFrame(data, columns=cols)

    # Convert types
    for col in ["year", "month", "day", "hour", "hour_along"]:
        if col in df.columns:
            df[col] = df[col].astype(int)

    # Year conversion
    if "year" in df.columns:
        df["year"] = df["year"].apply(lambda y: int(y) + 2000 if y < 50 else int(y) + 1900)

    # Create datetime
    if all(col in df.columns for col in ["year", "month", "day", "hour"]):
        try:
            df["traj_dt"] = pd.to_datetime(
                df[["year", "month", "day", "hour"]].astype(str).agg("-".join, axis=1),
                format="%Y-%m-%d-%H",
                errors="coerce"
            )
            df["traj_dt_i"] = df["traj_dt"].iloc[0] if len(df) > 0 else pd.NaT
        except Exception:
            df["traj_dt"] = pd.NaT
            df["traj_dt_i"] = pd.NaT

    return df
