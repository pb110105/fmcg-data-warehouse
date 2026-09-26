# src/view_source_data.R
# Xem dữ liệu nguồn Complete Journey trong VS Code.
# Không sửa dữ liệu nguồn và không xuất CSV.

data_dir <- "data/raw/complete_journey"

# Đọc một file RDA hoặc RDS
read_source <- function(filename) {
  path <- file.path(data_dir, filename)

  if (!file.exists(path)) {
    stop("Không tìm thấy file: ", path,
         "\nHãy chạy từ thư mục gốc fmcg-data-warehouse.")
  }

  if (grepl("\\.rds$", filename, ignore.case = TRUE)) {
    return(readRDS(path))
  }

  env <- new.env()
  object_names <- load(path, envir = env)

  if (length(object_names) != 1L) {
    stop("File ", filename, " chứa nhiều đối tượng: ",
         paste(object_names, collapse = ", "))
  }

  env[[object_names[1]]]
}

# 1. Đọc các bảng nguồn
products <- read_source("products.rda")
demographics <- read_source("demographics.rda")
campaigns <- read_source("campaigns.rda")
campaign_descriptions <- read_source("campaign_descriptions.rda")
coupons <- read_source("coupons.rda")
coupon_redemptions <- read_source("coupon_redemptions.rda")
transactions <- read_source("transactions.rds")

# 2. Promotions lớn: đổi FALSE thành TRUE khi cần đọc
load_promotions <- FALSE

tables <- list(
  products = products,
  demographics = demographics,
  campaigns = campaigns,
  campaign_descriptions = campaign_descriptions,
  coupons = coupons,
  coupon_redemptions = coupon_redemptions,
  transactions = transactions
)

if (load_promotions) {
  promotions <- read_source("promotions.rds")
  tables[["promotions"]] <- promotions
}

# 3. Tổng quan số dòng và số cột
overview <- data.frame(
  table_name = names(tables),
  rows = vapply(tables, nrow, integer(1)),
  columns = vapply(tables, ncol, integer(1)),
  row.names = NULL
)

print(overview)

# 4. Thông tin từng cột: tên, kiểu dữ liệu và số giá trị thiếu
column_details <- do.call(
  rbind,
  lapply(names(tables), function(table_name) {
    tbl <- tables[[table_name]]

    data.frame(
      table_name = table_name,
      column_name = names(tbl),
      data_type = vapply(
        tbl, function(x) paste(class(x), collapse = "/"), character(1)
      ),
      missing_values = vapply(
        tbl, function(x) sum(is.na(x)), numeric(1)
      ),
      row.names = NULL
    )
  })
)

print(column_details, row.names = FALSE)

# 5. Hàm mở bảng: mặc định hiển thị 200 dòng đầu
show_table <- function(table_name, n = 200L) {
  if (!table_name %in% names(tables)) {
    stop("Bảng chưa được nạp: ", table_name)
  }

  if (!interactive()) {
    stop("Hãy gọi show_table() trong Terminal R của VS Code.")
  }

  tbl <- tables[[table_name]]

  if (is.infinite(n)) {
    View(tbl, title = table_name)
  } else {
    View(head(tbl, n), title = paste(table_name, "-", n, "dong dau"))
  }
}

# 6. Mở bảng tổng quan khi chạy trong phiên R tương tác
if (interactive()) {
  View(overview)
}

# Chạy riêng các lệnh dưới đây khi muốn xem từng bảng:
# show_table("products")
# show_table("demographics")
# show_table("campaigns")
# show_table("campaign_descriptions", Inf)
# show_table("coupons")
# show_table("coupon_redemptions")
# show_table("transactions")
# show_table("promotions")  # Cần load_promotions <- TRUE
#
# Xem thông tin các cột:
# View(column_details)