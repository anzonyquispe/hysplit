# Test configuration file generation in R
library(splitr)

test_dir <- "/Users/anzony.quisperojas/Documents/GitHub/python/hysplit/tests/comparison/config_test_r"
dir.create(test_dir, showWarnings = FALSE, recursive = TRUE)

# Get set_config and write_config_list from splitr namespace
config <- set_config(numpar = 2500, maxpar = 10000, tm_pres = 1, tm_tamb = 1)
ascdata <- set_ascdata()

# Write config manually (mimicking internal function)
config_content <- paste0(
  "&SETUP\n",
  paste0(names(config), " = ", config, ",\n", collapse = ""),
  "/\n"
)
cat(config_content, file = file.path(test_dir, "SETUP.CFG"))

# Write ascdata
ascdata_content <- paste0(ascdata, "\n", collapse = "")
cat(ascdata_content, file = file.path(test_dir, "ASCDATA.CFG"))

cat("R SETUP.CFG generated:\n")
cat("----------------------------------------\n")
cat(readLines(file.path(test_dir, "SETUP.CFG")), sep = "\n")

cat("\n\nR ASCDATA.CFG generated:\n")
cat("----------------------------------------\n")
cat(readLines(file.path(test_dir, "ASCDATA.CFG")), sep = "\n")
