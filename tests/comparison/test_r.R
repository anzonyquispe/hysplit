# R script to test trajectory_read and output CSV for comparison
library(splitr)
library(dplyr)

# Set working directory
setwd("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison")

# Read trajectory file
cat("Reading trajectory file with splitr...\n")
traj_df <- trajectory_read(output_folder = ".")

# Print summary
cat("\nDataFrame dimensions:", dim(traj_df)[1], "rows,", dim(traj_df)[2], "columns\n")
cat("\nColumn names:\n")
print(names(traj_df))

cat("\nData types:\n")
print(sapply(traj_df, class))

cat("\nFirst few rows:\n")
print(head(traj_df, 15))

cat("\nSummary statistics:\n")
print(summary(traj_df[, c("lat", "lon", "height", "pressure")]))

# Write to CSV for comparison
write.csv(traj_df, "r_output.csv", row.names = FALSE)
cat("\nOutput written to r_output.csv\n")
