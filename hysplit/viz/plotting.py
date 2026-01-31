"""Visualization functions for HYSPLIT trajectory and dispersion data.

Provides interactive map visualizations using Folium (Python equivalent of
R's leaflet) and static plots using Matplotlib.
"""

from __future__ import annotations

from typing import Optional, Union, List, Tuple
import warnings

import numpy as np
import pandas as pd

# Optional visualization dependencies
try:
    import folium
    from folium import plugins
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

try:
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.collections import LineCollection
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# Default color palettes
DEFAULT_TRAJECTORY_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

DEFAULT_DISPERSION_CMAP = "YlOrRd"


def _get_map_bounds(df: pd.DataFrame) -> Tuple[List[float], List[float]]:
    """Calculate map bounds from data.

    Returns:
        Tuple of (center, bounds) where center is [lat, lon]
        and bounds is [[min_lat, min_lon], [max_lat, max_lon]]
    """
    min_lat, max_lat = df["lat"].min(), df["lat"].max()
    min_lon, max_lon = df["lon"].min(), df["lon"].max()

    center = [(min_lat + max_lat) / 2, (min_lon + max_lon) / 2]
    bounds = [[min_lat, min_lon], [max_lat, max_lon]]

    return center, bounds


def trajectory_plot(
    traj_df: pd.DataFrame,
    color_by: str = "run",
    colors: Optional[List[str]] = None,
    line_width: float = 2.0,
    opacity: float = 0.8,
    show_markers: bool = True,
    marker_size: int = 5,
    tiles: str = "OpenStreetMap",
    zoom_start: int = 4,
    title: Optional[str] = None,
    backend: str = "folium",
    figsize: Tuple[int, int] = (12, 8),
    save_path: Optional[str] = None
) -> Union["folium.Map", "plt.Figure", None]:
    """Plot trajectory data on an interactive map.

    Args:
        traj_df: DataFrame with trajectory data (must have lat, lon columns)
        color_by: Column to use for coloring trajectories ("run", "height", etc.)
        colors: Custom color palette (list of hex colors)
        line_width: Width of trajectory lines
        opacity: Line opacity (0-1)
        show_markers: Show start/end point markers
        marker_size: Size of markers
        tiles: Map tile provider ("OpenStreetMap", "Stamen Terrain", etc.)
        zoom_start: Initial zoom level
        title: Optional plot title
        backend: Visualization backend ("folium" or "matplotlib")
        figsize: Figure size for matplotlib backend
        save_path: Optional path to save the plot

    Returns:
        Folium Map object or Matplotlib Figure

    Example:
        from hysplit import hysplit_trajectory, trajectory_plot

        traj = hysplit_trajectory(lat=50.0, lon=-120.0, duration=48)
        map_obj = trajectory_plot(traj, color_by="height")
        map_obj.save("trajectory_map.html")
    """
    if traj_df is None or traj_df.empty:
        warnings.warn("Empty or None DataFrame provided")
        return None

    required_cols = ["lat", "lon"]
    if not all(col in traj_df.columns for col in required_cols):
        raise ValueError(f"DataFrame must have columns: {required_cols}")

    if colors is None:
        colors = DEFAULT_TRAJECTORY_COLORS

    if backend == "folium":
        return _trajectory_plot_folium(
            traj_df=traj_df,
            color_by=color_by,
            colors=colors,
            line_width=line_width,
            opacity=opacity,
            show_markers=show_markers,
            marker_size=marker_size,
            tiles=tiles,
            zoom_start=zoom_start,
            title=title,
            save_path=save_path
        )
    elif backend == "matplotlib":
        return _trajectory_plot_matplotlib(
            traj_df=traj_df,
            color_by=color_by,
            colors=colors,
            line_width=line_width,
            opacity=opacity,
            show_markers=show_markers,
            marker_size=marker_size,
            title=title,
            figsize=figsize,
            save_path=save_path
        )
    else:
        raise ValueError(f"Unknown backend: {backend}. Use 'folium' or 'matplotlib'")


def _trajectory_plot_folium(
    traj_df: pd.DataFrame,
    color_by: str,
    colors: List[str],
    line_width: float,
    opacity: float,
    show_markers: bool,
    marker_size: int,
    tiles: str,
    zoom_start: int,
    title: Optional[str],
    save_path: Optional[str]
) -> "folium.Map":
    """Create trajectory plot using Folium."""
    if not HAS_FOLIUM:
        raise ImportError("Folium is required for interactive maps. Install with: pip install folium")

    center, bounds = _get_map_bounds(traj_df)

    # Create map
    m = folium.Map(location=center, zoom_start=zoom_start, tiles=tiles)

    # Fit bounds
    m.fit_bounds(bounds)

    # Get unique values for coloring
    if color_by in traj_df.columns:
        unique_vals = traj_df[color_by].unique()
    else:
        unique_vals = [0]
        traj_df = traj_df.copy()
        traj_df[color_by] = 0

    # Create color mapping
    color_map = {val: colors[i % len(colors)] for i, val in enumerate(sorted(unique_vals))}

    # Group by run/trajectory
    if "run" in traj_df.columns:
        groups = traj_df.groupby("run")
    else:
        groups = [(0, traj_df)]

    for group_id, group_df in groups:
        if group_df.empty:
            continue

        # Sort by hour_along if available
        if "hour_along" in group_df.columns:
            group_df = group_df.sort_values("hour_along")

        # Get coordinates
        coords = list(zip(group_df["lat"], group_df["lon"]))

        if len(coords) < 2:
            continue

        # Get color
        if color_by in group_df.columns:
            color_val = group_df[color_by].iloc[0]
        else:
            color_val = 0
        line_color = color_map.get(color_val, colors[0])

        # Draw trajectory line
        folium.PolyLine(
            coords,
            color=line_color,
            weight=line_width,
            opacity=opacity,
            popup=f"Run: {group_id}"
        ).add_to(m)

        # Add markers
        if show_markers:
            # Start marker
            folium.CircleMarker(
                location=coords[0],
                radius=marker_size,
                color=line_color,
                fill=True,
                fillColor=line_color,
                fillOpacity=1.0,
                popup=f"Start: {coords[0]}"
            ).add_to(m)

            # End marker
            folium.CircleMarker(
                location=coords[-1],
                radius=marker_size * 0.7,
                color=line_color,
                fill=True,
                fillColor="white",
                fillOpacity=1.0,
                popup=f"End: {coords[-1]}"
            ).add_to(m)

    # Add title if provided
    if title:
        title_html = f'<h3 style="position:fixed;top:10px;left:50px;z-index:9999">{title}</h3>'
        m.get_root().html.add_child(folium.Element(title_html))

    if save_path:
        m.save(save_path)

    return m


def _trajectory_plot_matplotlib(
    traj_df: pd.DataFrame,
    color_by: str,
    colors: List[str],
    line_width: float,
    opacity: float,
    show_markers: bool,
    marker_size: int,
    title: Optional[str],
    figsize: Tuple[int, int],
    save_path: Optional[str]
) -> "plt.Figure":
    """Create trajectory plot using Matplotlib."""
    if not HAS_MATPLOTLIB:
        raise ImportError("Matplotlib is required. Install with: pip install matplotlib")

    fig, ax = plt.subplots(figsize=figsize)

    # Get unique values for coloring
    if color_by in traj_df.columns:
        unique_vals = sorted(traj_df[color_by].unique())
    else:
        unique_vals = [0]
        traj_df = traj_df.copy()
        traj_df[color_by] = 0

    color_map = {val: colors[i % len(colors)] for i, val in enumerate(unique_vals)}

    # Group and plot
    if "run" in traj_df.columns:
        groups = traj_df.groupby("run")
    else:
        groups = [(0, traj_df)]

    for group_id, group_df in groups:
        if group_df.empty:
            continue

        if "hour_along" in group_df.columns:
            group_df = group_df.sort_values("hour_along")

        lons = group_df["lon"].values
        lats = group_df["lat"].values

        if color_by in group_df.columns:
            color_val = group_df[color_by].iloc[0]
        else:
            color_val = 0
        line_color = color_map.get(color_val, colors[0])

        ax.plot(lons, lats, color=line_color, linewidth=line_width, alpha=opacity)

        if show_markers:
            ax.scatter(lons[0], lats[0], c=line_color, s=marker_size**2,
                      marker='o', zorder=5)
            ax.scatter(lons[-1], lats[-1], c='white', edgecolors=line_color,
                      s=(marker_size*0.7)**2, marker='o', zorder=5)

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.3)

    if title:
        ax.set_title(title)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def dispersion_plot(
    disp_df: pd.DataFrame,
    time_step: Optional[int] = None,
    color_by: str = "height",
    cmap: str = DEFAULT_DISPERSION_CMAP,
    marker_size: int = 3,
    opacity: float = 0.7,
    tiles: str = "OpenStreetMap",
    zoom_start: int = 4,
    title: Optional[str] = None,
    backend: str = "folium",
    figsize: Tuple[int, int] = (12, 8),
    save_path: Optional[str] = None
) -> Union["folium.Map", "plt.Figure", None]:
    """Plot dispersion particle positions on a map.

    Args:
        disp_df: DataFrame with particle positions (must have lat, lon columns)
        time_step: Optional time step to plot (filters by 'hour' column)
        color_by: Column to use for coloring particles
        cmap: Colormap for continuous color values
        marker_size: Size of particle markers
        opacity: Marker opacity (0-1)
        tiles: Map tile provider
        zoom_start: Initial zoom level
        title: Optional plot title
        backend: Visualization backend ("folium" or "matplotlib")
        figsize: Figure size for matplotlib backend
        save_path: Optional path to save the plot

    Returns:
        Folium Map object or Matplotlib Figure
    """
    if disp_df is None or disp_df.empty:
        warnings.warn("Empty or None DataFrame provided")
        return None

    required_cols = ["lat", "lon"]
    if not all(col in disp_df.columns for col in required_cols):
        raise ValueError(f"DataFrame must have columns: {required_cols}")

    # Filter by time step if specified
    if time_step is not None and "hour" in disp_df.columns:
        disp_df = disp_df[disp_df["hour"] == time_step]

    if disp_df.empty:
        warnings.warn(f"No data for time step {time_step}")
        return None

    if backend == "folium":
        return _dispersion_plot_folium(
            disp_df=disp_df,
            color_by=color_by,
            cmap=cmap,
            marker_size=marker_size,
            opacity=opacity,
            tiles=tiles,
            zoom_start=zoom_start,
            title=title,
            save_path=save_path
        )
    elif backend == "matplotlib":
        return _dispersion_plot_matplotlib(
            disp_df=disp_df,
            color_by=color_by,
            cmap=cmap,
            marker_size=marker_size,
            opacity=opacity,
            title=title,
            figsize=figsize,
            save_path=save_path
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _dispersion_plot_folium(
    disp_df: pd.DataFrame,
    color_by: str,
    cmap: str,
    marker_size: int,
    opacity: float,
    tiles: str,
    zoom_start: int,
    title: Optional[str],
    save_path: Optional[str]
) -> "folium.Map":
    """Create dispersion plot using Folium."""
    if not HAS_FOLIUM:
        raise ImportError("Folium is required. Install with: pip install folium")

    center, bounds = _get_map_bounds(disp_df)
    m = folium.Map(location=center, zoom_start=zoom_start, tiles=tiles)
    m.fit_bounds(bounds)

    # Get color values
    if color_by in disp_df.columns:
        values = disp_df[color_by]
        vmin, vmax = values.min(), values.max()

        # Create colormap
        if HAS_MATPLOTLIB:
            cm = plt.get_cmap(cmap)
            norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

            def get_color(val):
                rgba = cm(norm(val))
                return mcolors.to_hex(rgba)
        else:
            def get_color(val):
                return "#ff0000"
    else:
        def get_color(val):
            return "#ff0000"

    # Plot particles
    for _, row in disp_df.iterrows():
        color = get_color(row[color_by]) if color_by in disp_df.columns else "#ff0000"

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=marker_size,
            color=color,
            fill=True,
            fillColor=color,
            fillOpacity=opacity,
        ).add_to(m)

    if title:
        title_html = f'<h3 style="position:fixed;top:10px;left:50px;z-index:9999">{title}</h3>'
        m.get_root().html.add_child(folium.Element(title_html))

    if save_path:
        m.save(save_path)

    return m


def _dispersion_plot_matplotlib(
    disp_df: pd.DataFrame,
    color_by: str,
    cmap: str,
    marker_size: int,
    opacity: float,
    title: Optional[str],
    figsize: Tuple[int, int],
    save_path: Optional[str]
) -> "plt.Figure":
    """Create dispersion plot using Matplotlib."""
    if not HAS_MATPLOTLIB:
        raise ImportError("Matplotlib is required. Install with: pip install matplotlib")

    fig, ax = plt.subplots(figsize=figsize)

    if color_by in disp_df.columns:
        scatter = ax.scatter(
            disp_df["lon"],
            disp_df["lat"],
            c=disp_df[color_by],
            cmap=cmap,
            s=marker_size**2,
            alpha=opacity
        )
        plt.colorbar(scatter, label=color_by)
    else:
        ax.scatter(
            disp_df["lon"],
            disp_df["lat"],
            c="red",
            s=marker_size**2,
            alpha=opacity
        )

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.grid(True, alpha=0.3)

    if title:
        ax.set_title(title)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig
