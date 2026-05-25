args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 1) {
  stop("Usage: Rscript summary_inference_time.R <output_dir> [merged_csv] [summary_csv]")
}

output_dir <- args[1]

merged_csv <- if (length(args) >= 2) args[2] else "merged_inference_time.csv"
summary_csv <- if (length(args) >= 3) args[3] else "summary_inference_time.csv"

files <- list.files(
  path = output_dir,
  pattern = "^inference_time\\.csv$",
  recursive = TRUE,
  full.names = TRUE
)

if (length(files) == 0) {
  stop("No inference_time.csv found in: ", output_dir)
}

all <- data.frame()

for (f in files) {
  df <- read.csv(f, stringsAsFactors = FALSE)

  if (!"inference_time_seconds" %in% names(df)) {
    warning("Skip file without inference_time_seconds column: ", f)
    next
  }

  dataset <- basename(dirname(f))
  method <- basename(dirname(dirname(f)))

  df$dataset <- dataset
  df$method <- method
  df$source_file <- f

  all <- rbind(all, df)
}

all$inference_time_seconds <- as.numeric(all$inference_time_seconds)
all <- all[!is.na(all$inference_time_seconds), ]

if (nrow(all) == 0) {
  stop("No valid inference time records.")
}

write.csv(all, merged_csv, row.names = FALSE)

summary <- aggregate(
  inference_time_seconds ~ dataset + method,
  data = all,
  FUN = function(x) {
    c(
      n = length(x),
      mean = mean(x),
      median = median(x),
      min = min(x),
      max = max(x),
      total = sum(x)
    )
  }
)

summary <- do.call(data.frame, summary)

names(summary) <- c(
  "dataset",
  "method",
  "n",
  "mean_seconds",
  "median_seconds",
  "min_seconds",
  "max_seconds",
  "total_seconds"
)

write.csv(summary, summary_csv, row.names = FALSE)

cat("Saved merged records to:", merged_csv, "\n")
cat("Saved summary to:", summary_csv, "\n")
cat("Number of inference_time.csv files:", length(files), "\n")
cat("Number of records:", nrow(all), "\n")