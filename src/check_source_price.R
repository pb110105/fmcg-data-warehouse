# src/check_source_price.R
# Kiểm tra số lượng, doanh số và giảm giá.
# Các công thức suy ra bên dưới chỉ dùng để khảo sát.

data_dir <- "data/raw/complete_journey"
scope_path <- paste0(
  "data/landing/fmcg_classification_v1_3/",
  "product_scope.csv"
)

tx <- as.data.frame(
  readRDS(file.path(data_dir, "transactions.rds"))
)

product_env <- new.env()
object_names <- load(
  file.path(data_dir, "products.rda"),
  envir = product_env
)
stopifnot(length(object_names) == 1L)

products <- as.data.frame(product_env[[object_names[1]]])

scope <- read.csv(
  scope_path,
  colClasses = "character",
  check.names = FALSE
)

fields <- c(
  "quantity", "sales_value", "retail_disc",
  "coupon_disc", "coupon_match_disc"
)

stopifnot(
  all(fields %in% names(tx)),
  all(c("product_id", "scope_status") %in% names(scope)),
  !anyNA(products$product_id),
  !anyDuplicated(products$product_id),
  !anyNA(scope$product_id),
  !anyDuplicated(scope$product_id)
)

# Ghép bằng match để giữ nguyên số dòng giao dịch
product_index <- match(
  as.character(tx$product_id),
  as.character(products$product_id)
)

scope_index <- match(
  as.character(tx$product_id),
  scope$product_id
)

if (anyNA(scope_index)) {
  stop("Có sản phẩm giao dịch chưa có trong product_scope.csv.")
}

tx$scope_status <- scope$scope_status[scope_index]

for (field in c("department", "product_category",
                "product_type", "package_size")) {
  tx[[field]] <- as.character(products[[field]][product_index])
}

count_true <- function(x) {
  sum(x, na.rm = TRUE)
}

inspect_prices <- function(d, label) {
  cat("\n========================================\n")
  cat(label, "—", nrow(d), "dong\n")
  cat("========================================\n")

  # Kiểm tra dấu và giá trị thiếu
  stats <- do.call(rbind, lapply(fields, function(field) {
    x <- d[[field]]
    finite_x <- x[is.finite(x)]

    data.frame(
      field = field,
      missing = sum(is.na(x)),
      non_finite = sum(!is.finite(x) & !is.na(x)),
      negative = count_true(x < 0),
      zero = count_true(x == 0),
      positive = count_true(x > 0),
      minimum = if (length(finite_x)) min(finite_x) else NA_real_,
      maximum = if (length(finite_x)) max(finite_x) else NA_real_
    )
  }))

  print(stats, row.names = FALSE)

  q <- d$quantity
  s <- d$sales_value
  r <- d$retail_disc
  cpn <- d$coupon_disc
  m <- d$coupon_match_disc

  # Kiểm tra theo cent để tránh sai số số thực khi so sánh tiền
  sc <- round(s * 100)
  rc <- round(r * 100)
  cc <- round(cpn * 100)
  mc <- round(m * 100)

  checks <- c(
    quantity_fractional =
      count_true(abs(q - round(q)) > 1e-8),
    quantity_zero_sales_positive =
      count_true(q == 0 & sc > 0),
    quantity_positive_sales_zero =
      count_true(q > 0 & sc == 0),
    coupon_above_sales =
      count_true(cc > sc),
    match_positive_coupon_zero =
      count_true(mc > 0 & cc == 0),
    match_above_coupon =
      count_true(mc > cc),
    match_above_retail =
      count_true(mc > rc),
    quantity_above_100 =
      count_true(q > 100)
  )

  cat("\nCAC TRUONG HOP CAN KIEM TRA:\n")
  print(checks)

  cat("\nTONG TIEN THEO TUNG TRUONG — USD:\n")
  print(vapply(
    d[fields[-1]],
    function(x) sum(round(x * 100), na.rm = TRUE) / 100,
    numeric(1)
  ))

  cat("\nPHAN VI QUANTITY:\n")
  print(quantile(
    q,
    probs = c(0, 0.5, 0.9, 0.99, 1),
    na.rm = TRUE
  ))

  # Công thức ứng viên, CHƯA phải KPI đã được chốt
  candidates <- data.frame(
    customer_payment_candidate = (sc - cc) / 100,
    before_discount_candidate = (sc + rc + mc) / 100
  )

  cat("\nSO DONG AM THEO CONG THUC UNG VIEN:\n")
  print(vapply(
    candidates,
    function(x) count_true(x < 0),
    numeric(1)
  ))

  show_fields <- c(
    "product_id", "department", "product_category",
    "product_type", "package_size", fields
  )

  cat("\n10 DONG QUANTITY LON NHAT:\n")
  idx <- head(order(q, decreasing = TRUE, na.last = NA), 10)
  print(d[idx, show_fields, drop = FALSE], row.names = FALSE)

  cat("\n10 DONG CO COUPON MATCH:\n")
  idx <- head(which(mc > 0), 10)
  print(d[idx, show_fields, drop = FALSE], row.names = FALSE)

  cat("\n10 DONG CO COUPON LON HON SALES:\n")
  idx <- head(which(cc > sc), 10)
  print(d[idx, show_fields, drop = FALSE], row.names = FALSE)
}

inspect_prices(tx, "TOAN BO NGUON")

inspect_prices(
  tx[which(tx$scope_status == "IN_SCOPE"), , drop = FALSE],
  "FMCG IN_SCOPE V1.3"
)