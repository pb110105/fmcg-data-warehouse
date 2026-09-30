# Chuyển dữ liệu RDA/RDS sang CSV.
# Giữ nguyên file nguồn, xử lý lần lượt để giảm sử dụng RAM.

input_dir <- "data/raw/complete_journey"
output_dir <- "data/raw/complete_journey_csv"

if (!dir.exists(input_dir)) {
  stop("Không tìm thấy thư mục nguồn. Hãy chạy từ thư mục gốc project.")
}

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

files <- list.files(
  input_dir,
  pattern = "\\.(rda|rdata|rds)$",
  full.names = TRUE,
  ignore.case = TRUE
)

if (length(files) == 0L) {
  stop("Không có file RDA/RDS trong thư mục nguồn.")
}

export_csv <- function(tbl, filename) {
  if (!is.data.frame(tbl)) {
    stop("Đối tượng không phải bảng: ", filename)
  }

  # Tạo bản xuất riêng; không thay đổi dữ liệu nguồn
  out <- as.data.frame(tbl)

  # CSV không lưu kiểu ngày giờ: xuất chuỗi kèm độ lệch múi giờ
  for (column in names(out)) {
    if (inherits(out[[column]], "POSIXt")) {
      source_tz <- attr(out[[column]], "tzone")
      tz <- if (length(source_tz) > 0L &&
                !is.na(source_tz[1]) &&
                nzchar(source_tz[1])) {
        source_tz[1]
      } else {
        warning("Cột ", column,
                " không ghi rõ múi giờ; bản CSV được xuất theo UTC.")
        "UTC"
      }

      out[[column]] <- format(
        out[[column]],
        format = "%Y-%m-%dT%H:%M:%S%z",
        tz = tz
      )
    } else if (inherits(out[[column]], "Date")) {
      out[[column]] <- format(out[[column]], "%Y-%m-%d")
    }
  }

  destination <- file.path(output_dir, filename)
  message("Đang xuất: ", filename, " — ", nrow(out), " dòng")

  write.csv(
    out,
    file = destination,
    row.names = FALSE,
    na = "",
    fileEncoding = "UTF-8"
  )

  message("Đã lưu: ", destination)
}

for (path in files) {
  stem <- tools::file_path_sans_ext(basename(path))
  message("\nĐang đọc: ", basename(path))

  if (grepl("\\.rds$", path, ignore.case = TRUE)) {
    tbl <- readRDS(path)
    export_csv(tbl, paste0(stem, ".csv"))
    rm(tbl)
  } else {
    env <- new.env()
    objects <- load(path, envir = env)

    for (object_name in objects) {
      filename <- if (length(objects) == 1L) {
        paste0(stem, ".csv")
      } else {
        paste0(stem, "__", object_name, ".csv")
      }

      export_csv(env[[object_name]], filename)
    }

    rm(env)
  }

  invisible(gc())
}

message("\nHoàn tất xuất CSV.")