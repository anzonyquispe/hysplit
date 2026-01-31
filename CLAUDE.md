# CLAUDE.md - Project Context for AI Assistants

## Project Overview
**hysplit** - A Python port of the R [splitr](https://github.com/rich-iannone/splitr) package for interfacing with the HYSPLIT atmospheric transport model.

**Package Name**: `hysplit` (PyPI)
**Location**: `/Users/anzony.quisperojas/Documents/GitHub/python/hysplit`
**GitHub Repository**: `https://github.com/quishpi/hysplit`

## Repository Information
- **Main branch**: main
- **Platform**: macOS (Darwin 24.6.0)
- **Language**: Python with C++ extensions
- **Python Version**: >= 3.8

## Session History

### Session 2 - 2026-01-31
- **Renamed package from `pysplit` to `hysplit`**
- Created comprehensive README.md matching R package style
- Created tutorial Jupyter Notebook: `docs/tutorials/getting_started.ipynb`
- Updated pyproject.toml for PyPI publishing
- Created GitHub Actions workflows:
  - `.github/workflows/publish.yml` - Auto-publish to PyPI on release
  - `.github/workflows/ci.yml` - CI testing on push/PR
- Added LICENSE (MIT), MANIFEST.in, py.typed
- **Performance benchmarking:**
  - Python is ~5% faster than R (21.7s vs 22.8s for 120 runs)
  - HYSPLIT binary is the bottleneck (98% of runtime)
  - C++ optimizations help with file I/O (10x speedup)
  - See `tests/comparison/PERFORMANCE_ANALYSIS.md`

### Session 1 - 2026-01-31
- Analyzed the R splitr package at `/Users/anzony.quisperojas/Documents/GitHub/splitr`
- Created complete Python port with the following components:
  - Core models: TrajectoryModel, DispersionModel
  - Configuration: SETUP.CFG, ASCDATA.CFG, CONTROL file generators
  - Meteorological data downloaders for 8 data sources
  - C++ optimized file parsers (5-10x faster than pure Python)
  - Visualization with Folium (interactive maps) and Matplotlib
- **Validated R vs Python parity:**
  - Trajectory parsing: MATCH (all numeric columns identical)
  - SETUP.CFG generation: MATCH (40+ parameters)
  - ASCDATA.CFG generation: MATCH
- **Full model validation with real HYSPLIT runs:**
  - Ran trajectory example from splitr README
  - R and Python produce identical results
  - 100 trajectory points match exactly
- **Added cluster computing workflow:**
  - Split download/run architecture for HPC clusters
  - Batch processing with SLURM job array support
  - See `hysplit/workflows/` module

## Project Structure

```
hysplit/
├── hysplit/                    # Main package
│   ├── __init__.py            # Package exports
│   ├── py.typed               # PEP 561 marker
│   ├── core/                  # Core models and configuration
│   │   ├── __init__.py
│   │   ├── config.py          # SETUP.CFG and ASCDATA.CFG
│   │   ├── trajectory.py      # TrajectoryModel, hysplit_trajectory()
│   │   └── dispersion.py      # DispersionModel, hysplit_dispersion()
│   ├── met/                   # Meteorological data
│   │   ├── __init__.py
│   │   └── downloaders.py     # Data download functions
│   ├── io/                    # Input/Output
│   │   ├── __init__.py
│   │   └── readers.py         # trajectory_read(), dispersion_read()
│   ├── viz/                   # Visualization
│   │   ├── __init__.py
│   │   └── plotting.py        # trajectory_plot(), dispersion_plot()
│   ├── cpp/                   # C++ extensions
│   │   ├── __init__.py
│   │   └── parsers.cpp        # High-performance parsers
│   ├── workflows/             # Cluster computing utilities
│   │   ├── __init__.py
│   │   ├── download.py        # Met data download & manifest
│   │   ├── run.py             # Offline model execution
│   │   └── batch.py           # Batch processing & SLURM
│   └── bin/                   # HYSPLIT binaries
│       └── osx/               # macOS binaries
├── docs/                      # Documentation
│   └── tutorials/
│       └── getting_started.ipynb  # Tutorial notebook
├── tests/                     # Test suite
│   └── comparison/            # R vs Python comparison tests
│       ├── comparison_report.pdf
│       ├── benchmark_comparison_report.pdf
│       ├── PERFORMANCE_ANALYSIS.md
│       └── *.csv              # Test outputs
├── .github/
│   └── workflows/
│       ├── publish.yml        # PyPI publishing workflow
│       └── ci.yml             # CI testing workflow
├── setup.py                   # Build configuration
├── pyproject.toml            # Project metadata (PyPI)
├── README.md                 # Documentation (matches R splitr style)
├── LICENSE                   # MIT License
├── MANIFEST.in               # Source distribution manifest
├── .gitignore                # Git ignore rules
└── CLAUDE.md                 # This file
```

## PyPI Publishing

### Automatic Publishing via GitHub Actions

1. **Create a new release on GitHub:**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
   Then create a release from the tag on GitHub.

2. **The workflow will automatically:**
   - Build the package
   - Publish to TestPyPI first
   - Publish to PyPI
   - Create GitHub release with signed artifacts

### Required GitHub Secrets

Configure these in repository Settings > Secrets:

1. **TestPyPI**: Create an environment named `testpypi` with trusted publishing enabled
2. **PyPI**: Create an environment named `pypi` with trusted publishing enabled

### Manual Publishing

```bash
# Build
python -m build

# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## Installation

```bash
# From PyPI
pip install hysplit

# With visualization
pip install "hysplit[viz]"

# With all dependencies
pip install "hysplit[all]"

# From source (development)
pip install -e ".[dev]"
```

## Quick Usage

```python
import hysplit

# Run trajectory model
trajectory = hysplit.hysplit_trajectory(
    lat=42.83752,
    lon=-80.30364,
    height=50,
    duration=24,
    days=["2012-03-12"],
    daily_hours=[0, 6, 12, 18],
    direction="forward",
    met_type="reanalysis",
    met_dir="./met",
    exec_dir="./out"
)

# Method chaining API
model = (
    hysplit.create_trajectory_model()
    .add_trajectory_params(lat=43.45, lon=-79.70, height=50, ...)
    .run()
)
df = model.get_output_tbl()
```

## Cluster Computing Workflow

### Phase 1: Download (on machine with internet)
```python
from hysplit.workflows import download_met_data, create_met_manifest

manifest = download_met_data(
    met_type="reanalysis",
    start_date="2024-01-01",
    end_date="2024-01-31",
    output_dir="/shared/met_data",
    buffer_days=2,
    compute_checksums=True
)
create_met_manifest(manifest, "/shared/met_data/manifest.json")
```

### Phase 2: Run (on cluster without internet)
```python
from hysplit.workflows import load_met_manifest, run_trajectory_offline

manifest = load_met_manifest("/scratch/met/manifest.json")
trajectory = run_trajectory_offline(
    lat=42.83752, lon=-80.30364, height=50,
    duration=24, days=["2024-01-15"],
    met_manifest=manifest,
    exec_dir="/scratch/output"
)
```

### Batch Processing
```python
from hysplit.workflows import create_batch_config, run_batch_trajectories

config = create_batch_config(locations=[...], days=[...], ...)
results = run_batch_trajectories(config, n_workers=8)
```

## Performance Benchmarks

| Metric | R (splitr) | Python (hysplit) | Speedup |
|--------|-----------|------------------|---------|
| Total (120 runs) | 22.81 sec | 21.70 sec | 1.05x |
| Per-run mean | 190 ms | 181 ms | 1.05x |
| Config generation | 0.029 ms | 0.001 ms | 29x |

**Key Finding**: HYSPLIT binary is the bottleneck (98% of runtime). Both languages call the same binary, so performance is nearly identical. Use parallel batch processing for real speedups.

## Development Commands

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
black hysplit/
isort hysplit/

# Build package
python -m build

# Test import
python -c "import hysplit; print(hysplit.__version__)"
```

## Key Files

| File | Purpose |
|------|---------|
| `hysplit/__init__.py` | Package exports and version |
| `hysplit/core/trajectory.py` | Main trajectory model |
| `hysplit/core/dispersion.py` | Dispersion model |
| `hysplit/core/config.py` | HYSPLIT configuration |
| `hysplit/workflows/*.py` | Cluster computing utilities |
| `pyproject.toml` | PyPI metadata |
| `.github/workflows/publish.yml` | Auto-publish workflow |

## Meteorological Data Sources

| Type | Resolution | Coverage |
|------|------------|----------|
| gdas1 | 1° | Global |
| gdas0p5 | 0.5° | Global |
| gfs0p25 | 0.25° | Global |
| reanalysis | 2.5° | Global |
| narr | 32km | North America |
| nam12 | 12km | North America |
| era5 | 0.25° | Global |

## Notes for Future Sessions

### Pending Improvements
1. Fix dispersion model CONTROL file format
2. Add comprehensive test suite
3. Add type stubs for mypy
4. Consider Cython for additional optimization
5. Add support for ensemble runs
6. Add concentration grid output parsing

### Known Issues
- C++ extension requires Python headers at build time
- Dispersion CONTROL file needs format adjustment
- Some met file formats may need additional testing

### References
- Original R splitr: https://github.com/rich-iannone/splitr
- HYSPLIT documentation: https://www.ready.noaa.gov/HYSPLIT.php
- PyPI package: https://pypi.org/project/hysplit/
