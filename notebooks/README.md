# HySplit Notebooks

Interactive Jupyter notebooks demonstrating the `hysplit` package functionality.

## Quick Start

**Start here:** [00_quick_start.ipynb](00_quick_start.ipynb) - A tested, working demonstration of the package.

## All Notebooks

| Notebook | Description |
|----------|-------------|
| [00_quick_start.ipynb](00_quick_start.ipynb) | **Start here!** Core trajectory functionality |
| [01_trajectory_modeling.ipynb](01_trajectory_modeling.ipynb) | Detailed trajectory modeling examples |
| [02_dispersion_modeling.ipynb](02_dispersion_modeling.ipynb) | Dispersion modeling API demonstration |

## Running Locally

1. Navigate to the `notebooks/` directory
2. Launch Jupyter:
```bash
jupyter notebook
```
3. Open `00_quick_start.ipynb` and run all cells

## Requirements

- Python 3.8+
- `matplotlib` for plots
- Internet connection (to download meteorological data)

## Notes

- Meteorological data is downloaded automatically on first run
- Met data is cached in the `./met` directory
- Output files are saved in the `./out` directory
