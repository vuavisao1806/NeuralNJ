#!/usr/bin/env Rscript

# ============================================================
# Plot boxplot of normalized RF distance (nRF) for RAxML results
#
# Expected input file format: TSV or CSV with at least columns:
#   dataset   gene   rf   nrf
# Example:
#   SongD1    gene1  12   0.3529
#   SongD1    gene2  10   0.2941
#   JarvD5a   gene1  8    0.2105
#
# Usage:
#   Rscript plot_nrf_boxplot.R rf_results.tsv nrf_boxplot.pdf
#   Rscript plot_nrf_boxplot.R rf_results.csv nrf_boxplot.png
# ============================================================

args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 1) {
  stop("Usage: Rscript plot_nrf_boxplot.R <input.tsv/csv> [output.pdf/png]", call. = FALSE)
}

input_file <- args[1]
output_file <- ifelse(length(args) >= 2, args[2], "nrf_boxplot.pdf")

if (!file.exists(input_file)) {
  stop(paste("Input file does not exist:", input_file), call. = FALSE)
}

# ---------- Read data ----------
# Auto-detect CSV vs TSV by extension.
ext <- tolower(tools::file_ext(input_file))

if (ext == "csv") {
  df <- read.csv(input_file, stringsAsFactors = FALSE, check.names = FALSE)
} else {
  df <- read.delim(input_file, stringsAsFactors = FALSE, check.names = FALSE)
}

# ---------- Validate columns ----------
required_cols <- c("dataset", "nrf")
missing_cols <- setdiff(required_cols, names(df))

if (length(missing_cols) > 0) {
  stop(
    paste("Missing required column(s):", paste(missing_cols, collapse = ", ")),
    call. = FALSE
  )
}

# Convert nRF to numeric safely.
df$nrf <- as.numeric(df$nrf)
df <- df[!is.na(df$nrf), ]

if (nrow(df) == 0) {
  stop("No valid numeric nRF values found.", call. = FALSE)
}

# Keep dataset order by first appearance in the file.
df$dataset <- factor(df$dataset, levels = unique(df$dataset))

# ---------- Summary table ----------
summary_df <- aggregate(
  nrf ~ dataset,
  data = df,
  FUN = function(x) c(
    n = length(x),
    mean = mean(x),
    median = median(x),
    sd = ifelse(length(x) > 1, sd(x), NA),
    min = min(x),
    max = max(x)
  )
)

summary_out <- do.call(data.frame, summary_df)
names(summary_out) <- c("dataset", "n", "mean", "median", "sd", "min", "max")

summary_file <- sub("\\.[^.]*$", "_summary.tsv", output_file)
write.table(summary_out, summary_file, sep = "\t", row.names = FALSE, quote = FALSE)

# ---------- Plot ----------
open_device <- function(file) {
  ext <- tolower(tools::file_ext(file))
  if (ext == "png") {
    png(file, width = 1800, height = 1200, res = 200)
  } else if (ext == "jpg" || ext == "jpeg") {
    jpeg(file, width = 1800, height = 1200, res = 200)
  } else {
    pdf(file, width = 8, height = 5)
  }
}

open_device(output_file)

par(
  family = "serif",
  mar = c(5, 5, 3, 1),
  las = 1
)

boxplot(
  nrf ~ dataset,
  data = df,
  outline = TRUE,
  ylab = "Normalized RF distance (nRF)",
  xlab = "Dataset",
  main = "Distribution of normalized RF distances",
  border = "black"
)

grid(nx = NA, ny = NULL, lty = "dotted")
stripchart(
  nrf ~ dataset,
  data = df,
  vertical = TRUE,
  method = "jitter",
  pch = 16,
  cex = 0.45,
  add = TRUE
)

dev.off()

cat("Saved boxplot to:", output_file, "\n")
cat("Saved summary to:", summary_file, "\n")
