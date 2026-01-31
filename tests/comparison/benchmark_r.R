#!/usr/bin/env Rscript
# R Performance Benchmark for splitr
# This script benchmarks various components to identify bottlenecks

library(splitr)
library(lubridate)
library(dplyr)
library(microbenchmark)

# Configuration
base_dir <- "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison"
met_dir <- file.path(base_dir, "met")
out_dir <- file.path(base_dir, "out_benchmark")
results_file <- file.path(base_dir, "benchmark_r_results.csv")

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

cat("=",'replicate'(69, "="), "\n", sep="")
cat("R (splitr) PERFORMANCE BENCHMARK\n")
cat("=",'replicate'(69, "="), "\n\n", sep="")

# Benchmark parameters - designed for ~10 minute total runtime
# Multiple locations, multiple days, multiple hours = many trajectory runs
LOCATIONS <- list(
  list(lat = 42.83752, lon = -80.30364),  # Ontario
  list(lat = 43.65107, lon = -79.34702),  # Toronto
  list(lat = 45.50169, lon = -73.56725),  # Montreal
  list(lat = 49.28273, lon = -123.12074), # Vancouver
  list(lat = 51.04532, lon = -114.05719)  # Calgary
)

DAYS <- seq(as.Date("2012-03-10"), as.Date("2012-03-15"), by = "1 day")
HOURS <- c(0, 6, 12, 18)
DURATION <- 48  # hours

total_runs <- length(LOCATIONS) * length(DAYS) * length(HOURS)
cat("Benchmark Configuration:\n")
cat("  Locations:", length(LOCATIONS), "\n")
cat("  Days:", length(DAYS), "\n")
cat("  Hours per day:", length(HOURS), "\n")
cat("  Duration:", DURATION, "hours\n")
cat("  Total trajectory runs:", total_runs, "\n\n")

# Initialize timing results
timing_results <- data.frame(
  component = character(),
  operation = character(),
  time_seconds = numeric(),
  stringsAsFactors = FALSE
)

add_timing <- function(component, operation, time_sec) {
  timing_results <<- rbind(timing_results, data.frame(
    component = component,
    operation = operation,
    time_seconds = time_sec,
    stringsAsFactors = FALSE
  ))
}

# ============================================================
# BENCHMARK 1: Configuration Generation
# ============================================================
cat("BENCHMARK 1: Configuration Generation\n")
cat("-",'replicate'(49, "-"), "\n", sep="")

config_times <- numeric(100)
for (i in 1:100) {
  start <- Sys.time()
  config <- set_config(numpar = 2500, maxpar = 10000)
  ascdata <- set_ascdata()
  end <- Sys.time()
  config_times[i] <- as.numeric(difftime(end, start, units = "secs"))
}
mean_config_time <- mean(config_times)
cat("  Mean config generation time:", round(mean_config_time * 1000, 3), "ms\n")
add_timing("config", "set_config", mean_config_time)

# ============================================================
# BENCHMARK 2: Meteorological Data (already downloaded)
# ============================================================
cat("\nBENCHMARK 2: Meteorological Data Check\n")
cat("-",'replicate'(49, "-"), "\n", sep="")

# Check if met files exist
met_files <- list.files(met_dir, pattern = "^RP.*\\.gbl$")
cat("  Available met files:", length(met_files), "\n")

# ============================================================
# BENCHMARK 3: Full Trajectory Runs
# ============================================================
cat("\nBENCHMARK 3: Full Trajectory Model Runs\n")
cat("-",'replicate'(49, "-"), "\n", sep="")

total_start <- Sys.time()
all_trajectories <- list()
run_times <- numeric()
parse_times <- numeric()
run_count <- 0

for (loc in LOCATIONS) {
  for (day in as.character(DAYS)) {
    cat("  Running:", day, "at", loc$lat, ",", loc$lon, "... ")

    run_start <- Sys.time()

    tryCatch({
      trajectory <- hysplit_trajectory(
        lat = loc$lat,
        lon = loc$lon,
        height = 50,
        duration = DURATION,
        days = day,
        daily_hours = HOURS,
        direction = "forward",
        met_type = "reanalysis",
        extended_met = FALSE,
        met_dir = met_dir,
        exec_dir = out_dir,
        clean_up = TRUE
      )

      run_end <- Sys.time()
      run_time <- as.numeric(difftime(run_end, run_start, units = "secs"))
      run_times <- c(run_times, run_time)
      run_count <- run_count + length(HOURS)

      all_trajectories[[length(all_trajectories) + 1]] <- trajectory

      cat("done in", round(run_time, 2), "sec\n")

    }, error = function(e) {
      cat("ERROR:", conditionMessage(e), "\n")
    })
  }
}

total_end <- Sys.time()
total_trajectory_time <- as.numeric(difftime(total_end, total_start, units = "secs"))

cat("\n  Total trajectory runs completed:", run_count, "\n")
cat("  Total trajectory time:", round(total_trajectory_time, 2), "seconds\n")
cat("  Mean time per day-location:", round(mean(run_times), 2), "seconds\n")
cat("  Mean time per individual run:", round(total_trajectory_time / run_count, 3), "seconds\n")

add_timing("trajectory", "total_runs", total_trajectory_time)
add_timing("trajectory", "per_run_mean", mean(run_times) / length(HOURS))

# ============================================================
# BENCHMARK 4: File Parsing (trajectory_read)
# ============================================================
cat("\nBENCHMARK 4: Output File Parsing\n")
cat("-",'replicate'(49, "-"), "\n", sep="")

# Create sample output files for parsing benchmark
# First, run a quick trajectory to get output files
test_out_dir <- file.path(base_dir, "parse_test")
dir.create(test_out_dir, showWarnings = FALSE, recursive = TRUE)

# Run one trajectory to create files
tryCatch({
  test_traj <- hysplit_trajectory(
    lat = 42.83752,
    lon = -80.30364,
    height = 50,
    duration = 24,
    days = "2012-03-12",
    daily_hours = c(0, 6, 12, 18),
    direction = "forward",
    met_type = "reanalysis",
    met_dir = met_dir,
    exec_dir = test_out_dir,
    clean_up = FALSE
  )

  # Find trajectory output folders
  output_folders <- list.dirs(test_out_dir, recursive = TRUE, full.names = TRUE)
  output_folders <- output_folders[grepl("traj-", output_folders)]

  if (length(output_folders) > 0) {
    # Benchmark parsing
    parse_times <- numeric(50)
    for (i in 1:50) {
      start <- Sys.time()
      parsed <- trajectory_read(output_folder = output_folders[1])
      end <- Sys.time()
      parse_times[i] <- as.numeric(difftime(end, start, units = "secs"))
    }

    mean_parse_time <- mean(parse_times)
    cat("  Mean parse time (4 trajectory files):", round(mean_parse_time * 1000, 2), "ms\n")
    cat("  Rows parsed:", nrow(parsed), "\n")
    add_timing("parsing", "trajectory_read", mean_parse_time)
  }
}, error = function(e) {
  cat("  Parsing benchmark error:", conditionMessage(e), "\n")
})

# Cleanup
unlink(test_out_dir, recursive = TRUE)

# ============================================================
# BENCHMARK 5: Data Manipulation with dplyr
# ============================================================
cat("\nBENCHMARK 5: Data Manipulation (dplyr)\n")
cat("-",'replicate'(49, "-"), "\n", sep="")

if (length(all_trajectories) > 0) {
  # Combine all trajectories
  combined_start <- Sys.time()
  combined_traj <- bind_rows(all_trajectories)
  combined_end <- Sys.time()
  combine_time <- as.numeric(difftime(combined_end, combined_start, units = "secs"))

  cat("  Combined dataframe rows:", nrow(combined_traj), "\n")
  cat("  Combine time:", round(combine_time * 1000, 2), "ms\n")
  add_timing("manipulation", "bind_rows", combine_time)

  # Benchmark common operations
  # Filter
  filter_times <- numeric(100)
  for (i in 1:100) {
    start <- Sys.time()
    filtered <- combined_traj %>% filter(height > 100)
    end <- Sys.time()
    filter_times[i] <- as.numeric(difftime(end, start, units = "secs"))
  }
  cat("  Mean filter time:", round(mean(filter_times) * 1000, 3), "ms\n")
  add_timing("manipulation", "filter", mean(filter_times))

  # Group by and summarize
  groupby_times <- numeric(100)
  for (i in 1:100) {
    start <- Sys.time()
    summarized <- combined_traj %>%
      group_by(run) %>%
      summarize(
        mean_lat = mean(lat),
        mean_lon = mean(lon),
        mean_height = mean(height),
        max_height = max(height)
      )
    end <- Sys.time()
    groupby_times[i] <- as.numeric(difftime(end, start, units = "secs"))
  }
  cat("  Mean group_by + summarize time:", round(mean(groupby_times) * 1000, 3), "ms\n")
  add_timing("manipulation", "group_by_summarize", mean(groupby_times))
}

# ============================================================
# SUMMARY
# ============================================================
cat("\n",'replicate'(70, "="), "\n", sep="")
cat("BENCHMARK SUMMARY\n")
cat('replicate'(70, "="), "\n\n", sep="")

cat("Total Runs:", run_count, "\n")
cat("Total Time:", round(total_trajectory_time, 2), "seconds (",
    round(total_trajectory_time / 60, 2), " minutes)\n\n")

cat("Time Breakdown:\n")
for (i in 1:nrow(timing_results)) {
  cat("  ", timing_results$component[i], " - ", timing_results$operation[i], ": ",
      round(timing_results$time_seconds[i], 4), " seconds\n", sep="")
}

# Save results
timing_results$language <- "R"
timing_results$total_runs <- run_count
timing_results$total_time <- total_trajectory_time
write.csv(timing_results, results_file, row.names = FALSE)
cat("\nResults saved to:", results_file, "\n")

# Memory usage
cat("\nMemory Usage:\n")
print(gc())
