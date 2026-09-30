# src/check_source_time.R
# Chỉ kiểm tra dữ liệu nguồn, chưa chuyển đổi hoặc sửa thời gian.

data_dir <- "data/raw/complete_journey"

transactions <- readRDS(
  file.path(data_dir, "transactions.rds")
)

ts <- transactions$transaction_timestamp
week <- transactions$week

cat("\n=== 1. KIEU DU LIEU VA MUI GIO ===\n")
print(class(ts))

cat("\nThuoc tinh tzone cua cot:\n")
print(attr(ts, "tzone"))

cat("\nMui gio may dang chay R:\n")
print(Sys.timezone())

if (!inherits(ts, "POSIXt")) {
  stop("Timestamp không thuộc kiểu POSIXt; cần kiểm tra trước khi tiếp tục.")
}

source_tz <- attr(ts, "tzone")
has_source_tz <- length(source_tz) > 0L &&
  !is.na(source_tz[1]) &&
  nzchar(source_tz[1])

# Khi nguồn không ghi múi giờ, dùng UTC để khảo sát tạm.
# Đây chưa phải quyết định múi giờ nghiệp vụ.
inspect_tz <- if (has_source_tz) source_tz[1] else "UTC"

cat("\nMui gio dung de khao sat:", inspect_tz, "\n")

if (!has_source_tz) {
  cat("CHUA XAC DINH mui gio nguon; UTC chi dung de khao sat.\n")
}

cat("\n=== 2. GIA TRI THIEU VA KHOANG THOI GIAN ===\n")
cat("So dong:", nrow(transactions), "\n")
cat("Timestamp thieu:", sum(is.na(ts)), "\n")
cat("Week thieu:", sum(is.na(week)), "\n")

print(format(
  range(ts, na.rm = TRUE),
  format = "%Y-%m-%d %H:%M:%S %z",
  tz = inspect_tz
))

dates <- as.Date(ts, tz = inspect_tz)

cat("\nSo giao dich theo nam:\n")
print(table(format(dates, "%Y"), useNA = "ifany"))

cat("\nCac gia tri week:\n")
print(sort(unique(week)))

cat("\n=== 3. KHOANG NGAY CUA TUNG WEEK ===\n")

valid <- !is.na(dates) & !is.na(week)
date_groups <- split(dates[valid], week[valid])

week_summary <- do.call(
  rbind,
  lapply(names(date_groups), function(w) {
    d <- date_groups[[w]]
    first_day <- min(d)
    last_day <- max(d)

    data.frame(
      week = as.integer(w),
      first_date = as.character(first_day),
      last_date = as.character(last_day),
      first_weekday = as.integer(format(first_day, "%u")),
      last_weekday = as.integer(format(last_day, "%u")),
      distinct_dates = length(unique(d)),
      calendar_span = as.integer(last_day - first_day) + 1L,
      transaction_rows = length(d)
    )
  })
)

week_summary <- week_summary[order(week_summary$week), ]
rownames(week_summary) <- NULL

# Thứ: 1 = Thứ Hai, ..., 7 = Chủ nhật
print(week_summary, row.names = FALSE)

cat("\n=== 4. MOT NGAY CO NHIEU WEEK KHONG? ===\n")

date_week <- unique(data.frame(
  date = dates[valid],
  week = week[valid]
))

week_counts <- aggregate(
  week ~ date,
  data = date_week,
  FUN = function(x) length(unique(x))
)

names(week_counts)[2] <- "distinct_weeks"
conflicting_dates <- subset(week_counts, distinct_weeks > 1L)

cat("So ngay thuoc nhieu week:", nrow(conflicting_dates), "\n")
print(head(conflicting_dates, 20), row.names = FALSE)

cat("\n=== 5. DOI CHIEU HAI CACH DANH SO TUAN ===\n")

# Chỉ so sánh để tìm quy luật, chưa chọn cách nào làm chuẩn.
comparison <- data.frame(
  source_week = as.integer(week[valid]),
  iso_week = as.integer(format(dates[valid], "%V")),
  sunday_week_plus_1 = as.integer(format(dates[valid], "%U")) + 1L
)

cat(
  "So dong khac tuan ISO:",
  sum(comparison$source_week != comparison$iso_week), "\n"
)

cat(
  "So dong khac quy tac %U + 1:",
  sum(comparison$source_week != comparison$sunday_week_plus_1), "\n"
)

# Giữ miền week giao dịch, giải phóng bộ nhớ trước khi đọc promotions
transaction_weeks <- sort(unique(week[!is.na(week)]))

rm(transactions, ts, week, dates, date_groups,
   date_week, week_counts, comparison)
invisible(gc())

cat("\n=== 6. WEEK TRONG PROMOTIONS ===\n")

promotions <- readRDS(
  file.path(data_dir, "promotions.rds")
)

promotion_weeks <- sort(unique(
  promotions$week[!is.na(promotions$week)]
))

cat("Week thieu:", sum(is.na(promotions$week)), "\n")
cat("Cac gia tri week:\n")
print(promotion_weeks)

cat("\nWeek co trong giao dich nhung khong co trong promotions:\n")
print(setdiff(transaction_weeks, promotion_weeks))

cat("\nWeek co trong promotions nhung khong co trong giao dich:\n")
print(setdiff(promotion_weeks, transaction_weeks))

rm(promotions)
invisible(gc())
tx <- readRDS("data/raw/complete_journey/transactions.rds")

local_date <- as.Date(
  tx$transaction_timestamp,
  tz = "America/New_York"
)

expected_week <- as.integer(format(local_date, "%W")) + 1L
mismatch <- as.integer(tx$week) != expected_week

cat("So dong khac quy tac %W + 1:", sum(mismatch), "\n")

cat("Ngay khong co giao dich trong nam 2017:\n")
calendar_dates <- seq(
  as.Date("2017-01-01"),
  as.Date("2017-12-31"),
  by = "day"
)

print(calendar_dates[!calendar_dates %in% local_date])

rm(tx)
invisible(gc())