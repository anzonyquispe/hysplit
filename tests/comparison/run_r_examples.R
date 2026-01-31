#!/usr/bin/env Rscript
# R script to run trajectory and dispersion examples from splitr README
# This generates data and plots for comparison with Python

library(splitr)
library(lubridate)
library(dplyr)

# Set working directories
base_dir <- "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison"
met_dir <- file.path(base_dir, "met")
out_dir <- file.path(base_dir, "out")
plot_dir <- file.path(base_dir, "plots")

dir.create(met_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(plot_dir, showWarnings = FALSE, recursive = TRUE)

cat("=",'replicate'(59, "="), "\n", sep="")
cat("SPLITR (R) TRAJECTORY AND DISPERSION EXAMPLES\n")
cat("=",'replicate'(59, "="), "\n\n", sep="")

# ============================================================
# TRAJECTORY EXAMPLE (from README)
# ============================================================
cat("Running TRAJECTORY example...\n")
cat("Location: 42.83752°N, 80.30364°W (Ontario, Canada)\n")
cat("Date: 2012-03-12, Hours: 0, 6, 12, 18\n")
cat("Duration: 24h forward\n\n")

tryCatch({
  trajectory <- hysplit_trajectory(
    lat = 42.83752,
    lon = -80.30364,
    height = 50,
    duration = 24,
    days = "2012-03-12",
    daily_hours = c(0, 6, 12, 18),
    direction = "forward",
    met_type = "reanalysis",  # Using reanalysis as it's more reliable
    extended_met = FALSE,
    met_dir = met_dir,
    exec_dir = out_dir,
    clean_up = FALSE
  )

  cat("Trajectory completed!\n")
  cat("Shape:", dim(trajectory)[1], "rows x", dim(trajectory)[2], "columns\n")
  cat("\nFirst 10 rows:\n")
  print(head(trajectory, 10))

  # Save to CSV
  write.csv(trajectory, file.path(base_dir, "r_trajectory_output.csv"), row.names = FALSE)
  cat("\nSaved to r_trajectory_output.csv\n")

  # Summary statistics
  cat("\nTrajectory Summary:\n")
  cat("  Lat range:", min(trajectory$lat), "-", max(trajectory$lat), "\n")
  cat("  Lon range:", min(trajectory$lon), "-", max(trajectory$lon), "\n")
  cat("  Height range:", min(trajectory$height), "-", max(trajectory$height), "m\n")

}, error = function(e) {
  cat("ERROR running trajectory:", conditionMessage(e), "\n")
})

# ============================================================
# DISPERSION EXAMPLE (from README)
# ============================================================
cat("\n\nRunning DISPERSION example...\n")
cat("Location: 49.0°N, 123.0°W (Vancouver, Canada)\n")
cat("Date: 2015-07-01 00:00, Duration: 6h\n\n")

tryCatch({
  dispersion_model <-
    create_dispersion_model() %>%
    add_source(
      name = "particle",
      lat = 49.0, lon = -123.0, height = 50,
      rate = 5, pdiam = 15, density = 1.5, shape_factor = 0.8,
      release_start = lubridate::ymd_hm("2015-07-01 00:00"),
      release_end = lubridate::ymd_hm("2015-07-01 00:00") + lubridate::hours(2)
    ) %>%
    add_dispersion_params(
      start_time = lubridate::ymd_hm("2015-07-01 00:00"),
      end_time = lubridate::ymd_hm("2015-07-01 00:00") + lubridate::hours(6),
      direction = "forward",
      met_type = "reanalysis",
      met_dir = met_dir,
      exec_dir = out_dir
    ) %>%
    run_model()

  # Get output
  dispersion_tbl <- dispersion_model %>% get_output_tbl()

  cat("Dispersion completed!\n")
  cat("Shape:", dim(dispersion_tbl)[1], "rows x", dim(dispersion_tbl)[2], "columns\n")
  cat("\nFirst 10 rows:\n")
  print(head(dispersion_tbl, 10))

  # Save to CSV
  write.csv(dispersion_tbl, file.path(base_dir, "r_dispersion_output.csv"), row.names = FALSE)
  cat("\nSaved to r_dispersion_output.csv\n")

}, error = function(e) {
  cat("ERROR running dispersion:", conditionMessage(e), "\n")
})

cat("\n\nR examples completed.\n")
