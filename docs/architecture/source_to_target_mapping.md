# Ánh xạ dữ liệu nguồn–đích

## 1. Phạm vi

Tài liệu mô tả ánh xạ:

- Tám file nguồn Complete Journey → schema `staging`.
- Staging và kết quả phân loại FMCG → schema `dw`.
- Quy tắc chuyển đổi, kiểm tra lỗi và đối soát.

Thiết kế tham chiếu:

- `staging_design.md`.
- `dimensional_model.md`.
- `../dataset/fmcg_scope.md`.
- `../dataset/data_quality_findings.md`.
- `../requirements/kpi_definitions.md`.

Tên bảng trong tài liệu giữ theo mô hình logic.
DDL sử dụng tên PostgreSQL dạng snake_case chữ thường,
ví dụ `Fact_Sales` tương ứng `dw.fact_sales`.

## 2. Đầu vào của một lần nạp DW

Mỗi lần nạp DW phải xác định:

- Một `source_batch_id` có trạng thái SUCCESS tại Staging.
- Một `dw_load_id` dùng theo dõi lần nạp DW.
- Phiên bản pipeline.
- Phiên bản phân loại FMCG.
- SHA-256 của `product_scope.csv`.
- Mã lịch nguồn: `CJ_2017`.

Không trộn dữ liệu từ nhiều batch Staging.

Trong bảng DW:

- `etl_batch_id` lưu batch Staging cung cấp dữ liệu.
- `loaded_at` lưu thời điểm tạo hoặc cập nhật bản ghi.
- Nhật ký DW lưu `dw_load_id` cùng các thông tin đầu vào trên.

Kết quả phân loại phải được tạo từ đúng phiên bản file nguồn đang nạp.
Đối chiếu hash của products và transactions trong `validation.json`
với manifest của batch Staging trước khi sử dụng.

## 3. Nguồn → Staging

### 3.1. Ánh xạ bảng

| File nguồn | Bảng đích |
|---|---|
| `transactions.rds` | `staging.stg_transactions` |
| `promotions.rds` | `staging.stg_promotions` |
| `products.rda` | `staging.stg_products` |
| `demographics.rda` | `staging.stg_demographics` |
| `campaigns.rda` | `staging.stg_campaigns` |
| `campaign_descriptions.rda` | `staging.stg_campaign_descriptions` |
| `coupons.rda` | `staging.stg_coupons` |
| `coupon_redemptions.rda` | `staging.stg_coupon_redemptions` |

### 3.2. Ánh xạ cột nghiệp vụ

Tất cả cột nghiệp vụ được ánh xạ cùng tên.
Danh sách cột và kiểu đích được định nghĩa tại `staging_design.md`.

| Nhóm cột | Chuyển đổi |
|---|---|
| Mã định danh | Chuyển sang TEXT, bảo toàn biểu diễn mã |
| Factor của R | Lấy nhãn, không lấy số thứ tự level |
| Thuộc tính chuỗi | Giữ nguyên chuỗi nguồn |
| `quantity` và các trường tiền | Chuyển sang NUMERIC, không tự làm tròn |
| `week` | Chuyển sang INTEGER sau khi kiểm tra tính nguyên |
| Các cột ngày | Chuyển sang DATE, bảo toàn ngày nguồn |
| `transaction_timestamp` | Chuyển sang TIMESTAMPTZ, bảo toàn thời điểm tuyệt đối |
| NA | Chuyển thành SQL NULL |

Không lọc FMCG, xóa trùng, chuẩn hóa nhãn hoặc điền thiếu tại bước này.

### 3.3. Ánh xạ cột kỹ thuật

| Cột đích | Nguồn hoặc quy tắc |
|---|---|
| `staging_row_id` | Sinh tự động |
| `etl_batch_id` | Batch Staging hiện tại |
| `source_file_name` | Tên file được đọc |
| `source_object_name` | Tên đối tượng RDA; NULL với RDS |
| `source_row_number` | Vị trí dòng trong đối tượng, bắt đầu từ 1 |
| `loaded_at` | Thời điểm nạp |

Tên múi giờ nguồn được lưu tại `audit.etl_file_load.source_timezone`.
Với timestamp giao dịch hiện tại, giá trị là `America/New_York`.

Nếu lỗi đọc file, thiếu cột hoặc không chuyển kiểu được:
dừng nạp file, ghi lỗi và không đánh dấu batch SUCCESS.

## 4. Quy tắc chung Staging → DW

### 4.1. Khóa và thuộc tính

- Khóa thay thế được sinh khi gặp khóa nghiệp vụ mới.
- Khi chạy lại, tra cứu khóa đã có; không sinh lại khóa Dimension.
- Mã nguồn không được thay bằng mã khác chỉ vì thiếu thuộc tính mô tả.
- Chuỗi mô tả có thể trim khoảng trắng đầu/cuối.
- Chuỗi mô tả rỗng sau trim được chuyển thành NULL.
- Không đổi hoa/thường mã định danh.
- Chuẩn hóa phục vụ phân loại FMCG phải theo script phân loại,
  không tự bổ sung quy tắc khác trong ETL.

### 4.2. Bản ghi trùng

- Trùng hoàn toàn: chỉ loại tại lớp biến đổi khi quy tắc bảng cho phép,
  đồng thời ghi số dòng bị loại.
- Cùng khóa nghiệp vụ nhưng thuộc tính mâu thuẫn:
  ghi lỗi và chặn công bố lần nạp DW.
- Không chọn tùy ý dòng đầu tiên để giải quyết mâu thuẫn.

Riêng promotions được gom theo quy tắc tại mục 7,
vì nhiều dòng trên cùng sản phẩm–cửa hàng–tuần được giữ thông tin.

### 4.3. Chính sách lỗi

- Mã bắt buộc bị NULL hoặc rỗng: ghi lỗi và chặn công bố DW.
- Mã sản phẩm hoặc hộ có giá trị nhưng thiếu lookup:
  tạo Dimension riêng theo mã đó và đánh dấu thiếu thông tin.
- Measure thiếu, không hữu hạn hoặc âm: ghi lỗi và chặn công bố
  bảng Fact liên quan cho đến khi có quy tắc xử lý được phê duyệt.
- Bất thường đã có quy tắc giữ lại: nạp cùng cờ chất lượng.
- Không âm thầm bỏ dòng lỗi rồi báo đối soát thành công.

## 5. Ánh xạ Dimension

### 5.1. Dim_Product

Nguồn mã sản phẩm: hợp mã từ products, transactions, promotions và coupons
trong batch đã chọn.

| Cột đích | Cột nguồn hoặc quy tắc |
|---|---|
| `product_key` | Khóa thay thế |
| `product_id` | Mã sản phẩm phân biệt từ hợp nguồn |
| `manufacturer_id` | `stg_products.manufacturer_id` |
| `department` | `stg_products.department` |
| `brand` | `stg_products.brand` |
| `product_category` | `stg_products.product_category` |
| `product_type` | `stg_products.product_type` |
| `package_size` | `stg_products.package_size` |
| `scope_status` | Tra `product_scope.csv` theo `product_id` |
| `scope_rule_version` | Phiên bản phân loại được chọn |
| `source_lookup_missing_flag` | TRUE nếu không có sản phẩm trong `stg_products` |

Quy tắc:

- Sản phẩm thiếu lookup vẫn có khóa riêng; thuộc tính mô tả để NULL.
- Sản phẩm thiếu lookup được giữ REVIEW.
- Sản phẩm có trong lookup nhưng không có trong kết quả phân loại:
  coi là kết quả phân loại không đầy đủ và chặn nạp.
- Mã thiếu lookup xuất hiện thêm trong promotions hoặc coupons,
  chưa có trong CSV phân loại: giữ REVIEW và ghi nhận lý do.
- Không đưa sản phẩm REVIEW hoặc OUT_OF_SCOPE vào Fact bán hàng FMCG.
- Không biến `brand` thành tên thương hiệu.
- Không tự bóc tách `package_size` thành đơn vị đo chuẩn.

### 5.2. Dim_Household

Nguồn mã hộ: hợp mã từ transactions, demographics, campaigns
và coupon_redemptions.

| Cột đích | Cột nguồn hoặc quy tắc |
|---|---|
| `household_key` | Khóa thay thế |
| `household_id` | Mã hộ phân biệt từ hợp nguồn |
| `age` | `stg_demographics.age` |
| `income` | `stg_demographics.income` |
| `home_ownership` | `stg_demographics.home_ownership` |
| `marital_status` | `stg_demographics.marital_status` |
| `household_size` | `stg_demographics.household_size` |
| `household_comp` | `stg_demographics.household_comp` |
| `kids_count` | `stg_demographics.kids_count` |
| `demographics_available_flag` | TRUE nếu có dòng demographics tương ứng |

Nếu không có demographics, giữ mã hộ và để các thuộc tính mô tả NULL.

Cờ có demographics thể hiện có bản ghi nguồn, không có nghĩa mọi
thuộc tính nhân khẩu học đều đầy đủ.

### 5.3. Dim_Store

| Cột đích | Cột nguồn hoặc quy tắc |
|---|---|
| `store_key` | Khóa thay thế |
| `store_id` | Hợp mã phân biệt từ transactions và promotions |

Không bổ sung tên cửa hàng, thành phố, bang hoặc khu vực giả định.

### 5.4. Dim_Date

Tạo lịch liên tục từ ngày nhỏ nhất đến ngày lớn nhất cần dùng trong:

- Ngày giao dịch theo `America/New_York`.
- Ngày bắt đầu và kết thúc chiến dịch.
- Ngày đổi coupon.
- Ngày bắt đầu và kết thúc các tuần nguồn.

| Cột đích | Quy tắc |
|---|---|
| `date_key` | Số nguyên YYYYMMDD |
| `full_date` | Ngày lịch |
| `day_of_month` | Ngày trong tháng |
| `month_number` | Tháng 1–12 |
| `quarter_number` | Quý 1–4 |
| `calendar_year` | Năm lịch |
| `day_of_week` | Thứ Hai = 1, …, Chủ nhật = 7 |

Ngày giao dịch được tính bằng:

`(transaction_timestamp AT TIME ZONE 'America/New_York')::date`

Không chuyển các cột DATE của chiến dịch và đổi coupon sang múi giờ khác.

### 5.5. Dim_Week

Lịch `CJ_2017` có 53 tuần nguồn.

| Cột đích | Quy tắc |
|---|---|
| `week_key` | Khóa thay thế |
| `source_calendar_id` | `CJ_2017` |
| `source_week` | Số nguyên từ 1 đến 53 |
| `week_start_date` | 26/12/2016 + 7 × (`source_week` − 1) ngày |
| `week_end_date` | `week_start_date` + 6 ngày |
| `coverage_start_date` | Ngày lớn hơn giữa `week_start_date` và 01/01/2017 |
| `coverage_end_date` | Ngày nhỏ hơn giữa `week_end_date` và 31/12/2017 |
| `is_partial_coverage` | TRUE khi phần bao phủ ngắn hơn 7 ngày |

Phần bao phủ thể hiện khoảng nghiên cứu giao dịch, không phải số ngày
thực tế có bán hàng.

Ngày 25/12/2017 vẫn thuộc tuần 53 dù không có giao dịch.

Tra khóa tuần bằng `source_calendar_id + source_week`.
Kiểm tra ngày giao dịch nằm trong phần bao phủ tương ứng.

### 5.6. Dim_Campaign

| Cột đích | Cột nguồn hoặc quy tắc |
|---|---|
| `campaign_key` | Khóa thay thế |
| `campaign_id` | `stg_campaign_descriptions.campaign_id` |
| `campaign_type` | `stg_campaign_descriptions.campaign_type` |
| `start_date` | `stg_campaign_descriptions.start_date` |
| `end_date` | `stg_campaign_descriptions.end_date` |

Kiểm tra:

- Mã chiến dịch duy nhất.
- Ngày hợp lệ và `start_date <= end_date`.
- Mã chiến dịch trong campaigns, coupons và coupon_redemptions
  phải tìm được trong bảng mô tả.

Chiến dịch thiếu mô tả hoặc có ngày không hợp lệ được ghi lỗi
và chặn công bố các bảng liên quan.

### 5.7. Dim_Coupon

| Cột đích | Cột nguồn hoặc quy tắc |
|---|---|
| `coupon_key` | Khóa thay thế |
| `campaign_id` | `stg_coupons.campaign_id` |
| `coupon_upc` | `stg_coupons.coupon_upc` |

Lấy tập phân biệt `campaign_id + coupon_upc`.

Không coi mỗi dòng của coupons là một coupon riêng,
vì một coupon có thể liên kết nhiều sản phẩm.

Mã coupon–chiến dịch trong coupon_redemptions không tìm được
trong coupons phải được ghi lỗi trước khi nạp Fact đổi coupon.

## 6. Ánh xạ Fact_Sales

Nguồn: `stg_transactions`, lọc sản phẩm IN_SCOPE theo phiên bản đã chọn.

| Cột đích | Cột nguồn hoặc quy tắc |
|---|---|
| `sales_key` | Khóa thay thế |
| `basket_id` | `basket_id` nguồn |
| `product_key` | Tra Dim_Product bằng `product_id` |
| `household_key` | Tra Dim_Household bằng `household_id` |
| `store_key` | Tra Dim_Store bằng `store_id` |
| `date_key` | Tra Dim_Date bằng ngày giao dịch theo múi giờ nguồn |
| `week_key` | Tra Dim_Week bằng `CJ_2017 + week` |
| `transaction_timestamp` | Giữ thời điểm từ Staging |
| `quantity` | Giữ giá trị nguồn |
| `sales_value` | Giữ giá trị nguồn |
| `retail_disc` | Giữ giá trị nguồn |
| `coupon_disc` | Giữ giá trị nguồn |
| `coupon_match_disc` | Giữ giá trị nguồn |
| `scope_rule_version` | Phiên bản phân loại |
| `etl_batch_id` | Batch Staging được chọn |
| `loaded_at` | Thời điểm nạp DW |

### 6.1. Ánh xạ cờ chất lượng

| Cờ | Điều kiện TRUE |
|---|---|
| `quantity_zero_flag` | `quantity = 0` |
| `quantity_zero_sales_positive_flag` | `quantity = 0 AND sales_value > 0` |
| `positive_quantity_zero_sales_flag` | `quantity > 0 AND sales_value = 0` |
| `coupon_above_sales_flag` | `coupon_disc > sales_value` |
| `coupon_match_above_coupon_flag` | `coupon_match_disc > coupon_disc` |
| `high_quantity_flag` | `quantity > 100` |

Các phép so sánh tiền thực hiện trên giá trị NUMERIC đã kiểm tra
độ chính xác tiền tệ.

Nếu phát hiện số tiền có phần nhỏ hơn cent thực sự có ý nghĩa,
không tự làm tròn; ghi lỗi để thống nhất quy tắc trước khi nạp DW.

### 6.2. Điều kiện nạp

- Tổ hợp `basket_id + product_id` không trùng.
- Khóa bắt buộc và các measure hợp lệ.
- Ngày và tuần nhất quán.
- Mọi khóa Dimension tra cứu được.
- Giữ các dòng số lượng bằng 0 hoặc doanh số bằng 0.
- Không thêm campaign_key hoặc coupon_key bằng suy đoán.
- Không tính các công thức giá còn chờ xác minh.

Khóa duy nhất đích: `basket_id + product_key`.

## 7. Ánh xạ Fact_Promotion_Weekly

Nguồn: `stg_promotions`, lọc sản phẩm IN_SCOPE.

Gom theo `product_id + store_id + week` trong lịch `CJ_2017`.

| Cột đích | Quy tắc |
|---|---|
| `promotion_weekly_key` | Khóa thay thế |
| `product_key` | Tra Dim_Product |
| `store_key` | Tra Dim_Store |
| `week_key` | Tra Dim_Week bằng `CJ_2017 + week` |
| `display_location_codes` | Tập mã trưng bày khác NULL, phân biệt và sắp xếp |
| `mailer_location_codes` | Tập mã quảng cáo khác NULL, phân biệt và sắp xếp |
| `source_row_count` | COUNT(*) của nhóm nguồn |
| `multiple_source_rows_flag` | `source_row_count > 1` |
| `promotion_code_unknown_flag` | Có mã NULL hoặc ngoài danh sách hợp lệ |
| `has_display` | Theo quy tắc dưới đây |
| `has_mailer` | Theo quy tắc dưới đây |
| `scope_rule_version` | Phiên bản phân loại |
| `etl_batch_id` | Batch Staging được chọn |
| `loaded_at` | Thời điểm nạp DW |

### 7.1. Danh sách mã

Mã trưng bày hợp lệ:

`0, 1, 2, 3, 4, 5, 6, 7, 9, A`

- Mã xác nhận không trưng bày đặc biệt: `0, A`.
- Mã xác nhận có trưng bày đặc biệt: `1, 2, 3, 4, 5, 6, 7, 9`.

Mã quảng cáo hợp lệ:

`0, A, C, D, F, H, J, L, P, X, Z`

- Mã xác nhận không quảng cáo: `0`.
- Các mã hợp lệ còn lại xác nhận có quảng cáo.

### 7.2. Tạo cờ theo từng nhóm

Với mỗi loại trạng thái:

1. Có ít nhất một mã xác nhận có → TRUE.
2. Không có mã xác nhận có, nhưng có NULL hoặc mã lạ → NULL.
3. Còn lại → FALSE.

Nếu nhóm vừa có mã xác nhận có vừa có mã lạ, cờ trạng thái vẫn TRUE
nhưng `promotion_code_unknown_flag` cũng TRUE.

Mã lạ được giữ trong tập mã để truy vết.
NULL được phản ánh qua cờ chất lượng, không tự biến thành mã `0`.

Các cờ này nghĩa là có trạng thái được ghi nhận trong tuần,
không khẳng định quảng cáo/trưng bày diễn ra suốt cả tuần.

### 7.3. Kiểm tra

- Mỗi nhóm nguồn tạo đúng một dòng Fact.
- Tổng `source_row_count` bằng số dòng promotions IN_SCOPE trước gom.
- Khóa đích duy nhất: `product_key + store_key + week_key`.
- Không tạo bản ghi “không khuyến mãi” cho tổ hợp không có trong nguồn.

## 8. Ánh xạ Fact_Coupon_Redemption

Nguồn: toàn bộ `stg_coupon_redemptions` của batch được chọn.

| Cột đích | Cột nguồn hoặc quy tắc |
|---|---|
| `redemption_key` | Khóa thay thế |
| `household_key` | Tra Dim_Household bằng `household_id` |
| `coupon_key` | Tra Dim_Coupon bằng `campaign_id + coupon_upc` |
| `campaign_key` | Tra Dim_Campaign bằng `campaign_id` |
| `redemption_date_key` | Tra Dim_Date bằng `redemption_date` |
| `redemption_record_count` | 1 |
| `etl_batch_id` | Batch Staging được chọn |
| `loaded_at` | Thời điểm nạp DW |

Kiểm tra:

- Tổ hợp hộ–coupon–chiến dịch–ngày không trùng.
- Coupon và campaign_key cùng thuộc một chiến dịch.
- Ngày đổi coupon nằm trong thời gian chiến dịch.
- Trường hợp không đạt được ghi lỗi và chặn công bố để kiểm tra.

Không tạo product_key, store_key hoặc basket_id.
Không lọc bản ghi đổi coupon thành FMCG chỉ vì coupon có sản phẩm
FMCG trong danh sách đủ điều kiện.

Với bản nguồn hiện tại, dự kiến giữ 2.102 bản ghi.

## 9. Ánh xạ bảng liên kết

### 9.1. Bridge_Campaign_Household

| Cột đích | Quy tắc |
|---|---|
| `campaign_key` | Tra từ `stg_campaigns.campaign_id` |
| `household_key` | Tra từ `stg_campaigns.household_id` |

Lấy tập cặp phân biệt sau khi kiểm tra mã.
Ghi số dòng trùng bị loại nếu có.

Khóa chính: `campaign_key + household_key`.

### 9.2. Bridge_Coupon_Product

| Cột đích | Quy tắc |
|---|---|
| `coupon_key` | Tra bằng `stg_coupons.campaign_id + coupon_upc` |
| `product_key` | Tra bằng `stg_coupons.product_id` |

Lấy tập phân biệt `campaign_id + coupon_upc + product_id`.

Bản nguồn hiện tại:

- Đầu vào: 116.204 dòng.
- Dòng trùng hoàn toàn loại tại bước tạo liên kết: 4.872.
- Liên kết phân biệt dự kiến: 111.332.

Giữ liên kết với mọi trạng thái sản phẩm để không làm mất phạm vi
áp dụng của coupon.

Khóa chính: `coupon_key + product_key`.

## 10. Thứ tự nạp

1. Kiểm tra batch Staging, manifest và kết quả phân loại.
2. Nạp Dim_Product, Dim_Household và Dim_Store.
3. Nạp Dim_Date và Dim_Week.
4. Nạp Dim_Campaign và Dim_Coupon.
5. Nạp hai bảng liên kết.
6. Nạp Fact_Sales.
7. Nạp Fact_Promotion_Weekly.
8. Nạp Fact_Coupon_Redemption.
9. Kiểm tra khóa, tổng tiền, số dòng và quan hệ liên bảng.
10. Chỉ công bố DW khi các kiểm tra bắt buộc đạt.

Ba Fact có thể xử lý độc lập sau khi các Dimension cần thiết đã sẵn sàng.

## 11. Đối soát đầu ra

### 11.1. Fact_Sales v1.3

| Chỉ tiêu | Giá trị dự kiến |
|---|---:|
| Số dòng | 1.271.042 |
| Tổng sales_value | 3.419.948,46 USD |
| Tổng retail_disc | 710.911,57 USD |
| Tổng coupon_disc | 16.824,58 USD |
| Tổng coupon_match_disc | 4.358,46 USD |
| quantity_zero_flag = TRUE | 2.997 |
| quantity_zero_sales_positive_flag = TRUE | 19 |
| positive_quantity_zero_sales_flag = TRUE | 1.854 |
| coupon_above_sales_flag = TRUE | 402 |
| coupon_match_above_coupon_flag = TRUE | 4 |
| high_quantity_flag = TRUE | 1 |

Các cờ có thể giao nhau; không cộng số lượng cờ để suy ra số dòng lỗi.

Tổng quantity của Fact phải khớp tập giao dịch IN_SCOPE tại Staging.
Giá trị đối soát được tính khi chạy, không tự điền một tổng chưa kiểm tra.

### 11.2. Kiểm tra quan hệ

- Không có khóa ngoại không ánh xạ được.
- Không trùng khóa nghiệp vụ của Fact.
- Nối trái bán hàng với khuyến mãi theo sản phẩm–cửa hàng–tuần
  không tăng số dòng hoặc doanh số.
- Đếm bản ghi đổi coupon không bị nhân bởi Bridge_Coupon_Product.
- Số dòng bị loại, bị chặn và được giữ với cờ đều có nhật ký.

## 12. Chạy lại và thay đổi phạm vi

- Dimension dùng Type 1, giữ ổn định khóa thay thế.
- Với cùng batch và cùng phiên bản phân loại, chạy lại không tạo bản sao.
- Phiên bản đầu sử dụng nạp lại toàn bộ tập Fact mục tiêu có kiểm soát.
- Khi thay đổi phân loại, phải loại khỏi tập Fact mục tiêu các dòng
  không còn IN_SCOPE; không chỉ thêm các dòng mới.
- Thực hiện nạp vào bảng làm việc hoặc trong transaction phù hợp.
- Chỉ thay thế dữ liệu đang phục vụ báo cáo sau khi đối soát thành công.
- Không lưu nhiều bản sao Fact theo phiên bản phân loại rồi cộng chung.

Nếu muốn phân tích song song nhiều phiên bản trong tương lai,
cần thiết kế cơ chế versioning riêng.

## 13. Các nội dung chưa ánh xạ thành measure chính thức

Chưa tạo các measure sau:

- Tiền khách thực trả suy ra.
- Giá trước giảm suy ra.
- Tổng giảm giá kết hợp ba trường.
- Tỷ lệ giảm giá dựa trên giá trước giảm.
- Lợi nhuận hoặc ROI khuyến mãi.

Giá trị bán bình quân trên đơn vị nguồn được tính ở Data Mart hoặc BI,
trên cùng tập dòng có quantity > 0 và sales_value hợp lệ.

Nguồn không có thông tin kênh bán hoặc địa lý cửa hàng,
vì vậy không tạo các thuộc tính này bằng suy đoán.