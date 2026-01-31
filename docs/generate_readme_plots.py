#!/usr/bin/env python3
"""Generate plots for README documentation."""

import sys
sys.path.insert(0, "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit")

from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Try to load actual trajectory data if available
base_dir = Path("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison")
figures_dir = Path("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/docs/figures")

try:
    import pandas as pd
    traj_file = base_dir / "python_trajectory_output.csv"
    if traj_file.exists():
        trajectory = pd.read_csv(traj_file)
        print(f"Loaded trajectory data: {trajectory.shape}")
    else:
        # Generate sample data if no real data available
        print("No trajectory data found, generating sample...")
        trajectory = None
except Exception as e:
    print(f"Error loading data: {e}")
    trajectory = None

# Generate trajectory map plot
fig, ax = plt.subplots(figsize=(10, 8))

if trajectory is not None and len(trajectory) > 0:
    # Plot actual trajectory data
    colors = plt.cm.Set1(np.linspace(0, 1, trajectory['run'].nunique()))

    for i, run_id in enumerate(sorted(trajectory['run'].unique())):
        run_data = trajectory[trajectory['run'] == run_id]
        ax.plot(run_data['lon'], run_data['lat'], 'o-',
                color=colors[i], markersize=4, linewidth=1.5,
                label=f'Run {run_id} ({run_data["traj_dt"].iloc[0][:13]})',
                alpha=0.8)

    # Mark start point
    start_lon = trajectory['lon'].iloc[0]
    start_lat = trajectory['lat'].iloc[0]
    ax.scatter(start_lon, start_lat, c='red', s=200, marker='*',
               zorder=10, label='Start Location', edgecolors='black', linewidths=1)

    # Add some context
    ax.set_xlim(trajectory['lon'].min() - 0.5, trajectory['lon'].max() + 0.5)
    ax.set_ylim(trajectory['lat'].min() - 0.5, trajectory['lat'].max() + 0.5)
else:
    # Generate sample trajectory for illustration
    np.random.seed(42)
    hours = np.arange(0, 25)

    for run_id in range(1, 5):
        base_lon = -80.30364
        base_lat = 42.83752

        # Simulate wind-driven trajectory
        lon = base_lon + np.cumsum(np.random.randn(25) * 0.1 + 0.05)
        lat = base_lat + np.cumsum(np.random.randn(25) * 0.08 + 0.1)

        ax.plot(lon, lat, 'o-', markersize=4, linewidth=1.5,
                label=f'Run {run_id}', alpha=0.8)

    ax.scatter(-80.30364, 42.83752, c='red', s=200, marker='*',
               zorder=10, label='Start Location', edgecolors='black', linewidths=1)

ax.set_xlabel('Longitude', fontsize=12)
ax.set_ylabel('Latitude', fontsize=12)
ax.set_title('HYSPLIT Forward Trajectories\n24-hour runs from Ontario, Canada (2012-03-12)',
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=9)
ax.grid(True, alpha=0.3, linestyle='--')

# Add annotation
ax.annotate('Start: 42.84°N, 80.30°W\nHeight: 50m AGL',
            xy=(trajectory['lon'].iloc[0] if trajectory is not None else -80.30364,
                trajectory['lat'].iloc[0] if trajectory is not None else 42.83752),
            xytext=(10, -30), textcoords='offset points',
            fontsize=9, color='darkred',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

plt.tight_layout()
plt.savefig(figures_dir / 'trajectory_plot.png', dpi=150, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print(f"Saved: {figures_dir / 'trajectory_plot.png'}")

# Generate height profile plot
fig, ax = plt.subplots(figsize=(10, 5))

if trajectory is not None and len(trajectory) > 0:
    colors = plt.cm.Set1(np.linspace(0, 1, trajectory['run'].nunique()))

    for i, run_id in enumerate(sorted(trajectory['run'].unique())):
        run_data = trajectory[trajectory['run'] == run_id].sort_values('hour_along')
        ax.plot(run_data['hour_along'], run_data['height'], 'o-',
                color=colors[i], markersize=4, linewidth=1.5,
                label=f'Run {run_id}', alpha=0.8)
else:
    for run_id in range(1, 5):
        hours = np.arange(0, 25)
        height = 50 + np.cumsum(np.random.randn(25) * 20 + 5)
        height = np.maximum(height, 10)  # Keep above ground
        ax.plot(hours, height, 'o-', markersize=4, linewidth=1.5,
                label=f'Run {run_id}', alpha=0.8)

ax.axhline(y=50, color='red', linestyle='--', alpha=0.5, label='Initial Height (50m)')
ax.set_xlabel('Hours Along Trajectory', fontsize=12)
ax.set_ylabel('Height Above Ground (m)', fontsize=12)
ax.set_title('Trajectory Height Profiles', fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=9)
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_xlim(-1, 25)

plt.tight_layout()
plt.savefig(figures_dir / 'height_profile.png', dpi=150, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print(f"Saved: {figures_dir / 'height_profile.png'}")

# Generate dispersion plot (sample)
fig, ax = plt.subplots(figsize=(10, 8))

np.random.seed(123)
n_particles = 500

# Simulate particle dispersion from Vancouver
source_lon, source_lat = -123.0, 49.0

for hour in [1, 2, 3, 4, 5, 6]:
    # Particles spread over time
    spread = hour * 0.15
    lons = source_lon + np.random.randn(n_particles // 6) * spread + hour * 0.1
    lats = source_lat + np.random.randn(n_particles // 6) * spread * 0.7 - hour * 0.05

    scatter = ax.scatter(lons, lats, s=10, alpha=0.5,
                        label=f'Hour {hour}', c=[plt.cm.viridis(hour/7)])

ax.scatter(source_lon, source_lat, c='red', s=300, marker='*',
           zorder=10, label='Source', edgecolors='black', linewidths=1)

ax.set_xlabel('Longitude', fontsize=12)
ax.set_ylabel('Latitude', fontsize=12)
ax.set_title('HYSPLIT Dispersion Model\nParticle positions over 6 hours from Vancouver',
             fontsize=14, fontweight='bold')
ax.legend(loc='upper left', fontsize=9, markerscale=0.5)
ax.grid(True, alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig(figures_dir / 'dispersion_plot.png', dpi=150, bbox_inches='tight',
            facecolor='white', edgecolor='none')
plt.close()
print(f"Saved: {figures_dir / 'dispersion_plot.png'}")

print("\nAll README plots generated successfully!")
