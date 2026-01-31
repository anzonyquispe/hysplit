# R script to test extended meteorology trajectory_read
library(splitr)
library(dplyr)

setwd("/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison")

# Create directory with only extended file
dir.create("extended_test", showWarnings = FALSE)
file.copy("traj-test-extended", "extended_test/traj-test-extended", overwrite = TRUE)

cat("Reading extended meteorology trajectory file with splitr...\n")
traj_df <- trajectory_read(output_folder = "extended_test")

cat("\nDataFrame dimensions:", dim(traj_df)[1], "rows,", dim(traj_df)[2], "columns\n")
cat("\nColumn names:\n")
print(names(traj_df))

cat("\nFirst few rows:\n")
print(head(traj_df, 5))

write.csv(traj_df, "r_extended_output.csv", row.names = FALSE)
cat("\nOutput written to r_extended_output.csv\n")

# Cleanup
unlink("extended_test", recursive = TRUE)
