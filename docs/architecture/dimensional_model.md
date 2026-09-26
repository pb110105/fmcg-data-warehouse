# Thiết kế mô hình dữ liệu đa chiều

## 1. Mục tiêu và phạm vi

Mô hình phục vụ phân tích doanh số, giá bán và khuyến mãi từ bộ dữ liệu
Complete Journey.

Các quyết định chính:

- Fact bán hàng và Fact khuyến mãi theo tuần chỉ sử dụng sản phẩm
  `IN_SCOPE` theo phiên bản phân loại `1.3-cosmetics-and-exclusions`.
- Giữ toàn bộ dữ liệu nguồn trong Staging để truy vết.
- Dữ liệu đổi coupon được lưu riêng; không tự quy đổi một lần đổi coupon
  thành giao dịch của một sản phẩm FMCG cụ thể.
- Các Dimension được dùng chung giữa các Fact.
- Chưa lưu các chỉ số suy ra chưa được xác minh, như giá trước giảm,
  tiền khách thực trả và tỷ lệ giảm giá kết hợp.

## 2. Quy ước khóa

- Khóa nghiệp vụ: mã định danh có trong dữ liệu nguồn.
- Khóa thay thế: khóa do kho dữ liệu tạo, có hậu tố `_key`.
- Mã nguồn như `product_id`, `basket_id`, `household_id`, `store_id`,
  `campaign_id` và `coupon_upc` được lưu dạng chuỗi.
- Mỗi Fact có khóa chính riêng và ràng buộc duy nhất theo grain.
- `etl_batch_id` và `loaded_at` được bổ sung để truy vết lần nạp.
- Không đưa `etl_batch_id` vào khóa duy nhất nghiệp vụ; chạy lại
  cùng dữ liệu không được tạo thêm bản ghi.

## 3. Tổng quan các bảng Fact

| Bảng | Một dòng biểu diễn | Khóa nghiệp vụ duy nhất |
|---|---|---|
| `Fact_Sales` | Một sản phẩm trong một giỏ hàng | `basket_id + product_id` |
| `Fact_Promotion_Weekly` | Trạng thái quảng cáo và trưng bày của một sản phẩm tại một cửa hàng trong một tuần nguồn | `product_id + store_id + source_week_key` |
| `Fact_Coupon_Redemption` | Một bản ghi đổi coupon của một hộ gia đình, trong một chiến dịch, vào một ngày | `household_id + coupon_upc + campaign_id + redemption_date` |

Khóa của Fact đổi coupon phản ánh mức chi tiết quan sát được trong nguồn.
Nguồn không có mã sự kiện để phân biệt nhiều lần đổi giống hệt nhau
trong cùng ngày.

## 4. Fact_Sales

### 4.1. Grain và nguồn

Một dòng là kết quả mua một sản phẩm trong một giỏ hàng.

Nguồn: `transactions.rds`, kết hợp phân loại sản phẩm.

Chỉ nạp giao dịch có sản phẩm `IN_SCOPE`. Với phiên bản v1.3,
số dòng dự kiến là 1.271.042.

### 4.2. Các cột chính

| Cột | Vai trò |
|---|---|
| `sales_key` | Khóa chính thay thế |
| `basket_id` | Mã giỏ hàng; lưu trực tiếp trong Fact |
| `product_key` | FK đến `Dim_Product` |
| `household_key` | FK đến `Dim_Household` |
| `store_key` | FK đến `Dim_Store` |
| `date_key` | FK đến `Dim_Date` |
| `week_key` | FK đến `Dim_Week` |
| `transaction_timestamp` | Thời điểm giao dịch; lưu kiểu có múi giờ |
| `quantity` | Số lượng theo đơn vị nguồn |
| `sales_value` | Giá trị bán hàng nhà bán lẻ nhận theo nguồn |
| `retail_disc` | Khoản giảm giá thẻ khách hàng |
| `coupon_disc` | Khoản giảm từ coupon nhà sản xuất |
| `coupon_match_disc` | Khoản giảm đối ứng coupon |
| `quantity_zero_flag` | Cờ số lượng bằng 0 |
| `quantity_zero_sales_positive_flag` | Cờ số lượng bằng 0 nhưng doanh số dương |
| `positive_quantity_zero_sales_flag` | Cờ có số lượng nhưng doanh số bằng 0 |
| `coupon_above_sales_flag` | Cờ coupon lớn hơn doanh số |
| `coupon_match_above_coupon_flag` | Cờ đối ứng lớn hơn coupon |
| `high_quantity_flag` | Cờ số lượng vượt ngưỡng khảo sát |
| `scope_rule_version` | Phiên bản phân loại dùng khi nạp |
| `etl_batch_id` | Mã lần nạp |
| `loaded_at` | Thời điểm nạp |

Ràng buộc duy nhất: `basket_id + product_key`.

Trong nguồn hiện tại, tổ hợp `basket_id + product_id` không trùng.
ETL phải kiểm tra lại điều kiện này ở mỗi lần nạp.

### 4.3. Quy tắc tổng hợp

- `sales_value` có thể cộng theo các chiều phân tích.
- Ba khoản giảm giá được cộng riêng.
- `quantity` được diễn giải theo đơn vị nguồn; ưu tiên so sánh cùng sản phẩm.
- Số giỏ hàng được tính bằng `COUNT(DISTINCT basket_id)`.
- Số hộ gia đình được tính bằng `COUNT(DISTINCT household_key)`,
  loại khóa Unknown nếu có.
- Không cộng số giỏ hàng hoặc số hộ phân biệt giữa các nhóm để suy ra
  tổng phân biệt toàn hệ thống.
- Giá trị bán bình quân được tính tại lớp truy vấn/Data Mart,
  không cộng trực tiếp giá của từng dòng.

KPI số giỏ hàng từ Fact này là số giỏ có sản phẩm FMCG trong phạm vi,
không phải tổng giỏ hàng của toàn bộ nguồn.

### 4.4. Giới hạn liên kết

Fact không có `campaign_key` hoặc `coupon_key`, vì giao dịch nguồn
không xác định trực tiếp chiến dịch hoặc mã coupon.

Không suy diễn chiến dịch chỉ từ ngày giao dịch và hộ gia đình.

## 5. Fact_Promotion_Weekly

### 5.1. Grain và nguồn

Một dòng là thông tin quảng cáo và trưng bày của một sản phẩm tại
một cửa hàng trong một tuần nguồn.

Nguồn: `promotions.rds`, lọc sản phẩm `IN_SCOPE`.

Đây là Fact ghi nhận trạng thái khuyến mãi, không chứa doanh số
hoặc chi phí khuyến mãi.

### 5.2. Các cột chính

| Cột | Vai trò |
|---|---|
| `promotion_weekly_key` | Khóa chính thay thế |
| `product_key` | FK đến `Dim_Product` |
| `store_key` | FK đến `Dim_Store` |
| `week_key` | FK đến `Dim_Week` |
| `has_display` | Có trưng bày đặc biệt theo quy tắc mã nguồn |
| `has_mailer` | Có quảng cáo trong tài liệu quảng cáo |
| `display_location_codes` | Tập mã trưng bày phân biệt trong tổ hợp |
| `mailer_location_codes` | Tập mã quảng cáo phân biệt trong tổ hợp |
| `source_row_count` | Số dòng nguồn được gom vào tổ hợp |
| `multiple_source_rows_flag` | Tổ hợp có nhiều dòng nguồn |
| `promotion_code_unknown_flag` | Có mã thiếu hoặc chưa nhận diện |
| `scope_rule_version` | Phiên bản phân loại FMCG |
| `etl_batch_id` | Mã lần nạp |
| `loaded_at` | Thời điểm nạp |

Ràng buộc duy nhất: `product_key + store_key + week_key`.

### 5.3. Xử lý nhiều dòng nguồn

- Gom các dòng theo sản phẩm, cửa hàng và tuần.
- Giữ tập mã phân biệt để không mất thông tin.
- Lưu số dòng nguồn trước khi gom.
- Không chọn tùy ý dòng đầu tiên.
- Các tập mã có thể lưu bằng mảng trong PostgreSQL.
- Mã nguồn và từng dòng gốc vẫn được giữ tại Staging.

Quy tắc cờ dự kiến:

- `display_location = '0'` hoặc `'A'`: không phải trưng bày đặc biệt.
- Các mã trưng bày hợp lệ còn lại: có trưng bày đặc biệt.
- `mailer_location = '0'`: không quảng cáo.
- Các mã quảng cáo hợp lệ còn lại: có quảng cáo.
- Có ít nhất một mã khẳng định có: cờ bằng TRUE.
- Chỉ có mã hợp lệ khẳng định không: cờ bằng FALSE.
- Không có mã khẳng định có nhưng xuất hiện mã thiếu hoặc lạ:
  cờ bằng NULL và bật cờ chất lượng.

### 5.4. Liên kết với bán hàng

Khi phân tích, nối trái từ `Fact_Sales` sang bảng này bằng:

`product_key + store_key + week_key`

Phía khuyến mãi phải duy nhất trên tổ hợp này để không nhân dòng bán hàng.

Nếu không tìm thấy bản ghi khuyến mãi, trạng thái là “không có thông tin”,
không tự coi là “không khuyến mãi”.

Các khoản giảm giá trong giao dịch và quảng cáo/trưng bày là các khía cạnh
khác nhau; không đồng nhất chúng thành một trạng thái nếu chưa định nghĩa rõ.

## 6. Fact_Coupon_Redemption

### 6.1. Grain và nguồn

Một dòng là bản ghi đổi một coupon của một hộ gia đình trong một
chiến dịch vào một ngày.

Nguồn: `coupon_redemptions.rda`.

Giữ toàn bộ bản ghi đổi coupon để phân tích hoạt động chiến dịch.
Không gắn nhãn toàn bộ Fact này là dữ liệu đổi coupon FMCG.

### 6.2. Các cột chính

| Cột | Vai trò |
|---|---|
| `redemption_key` | Khóa chính thay thế |
| `household_key` | FK đến `Dim_Household` |
| `coupon_key` | FK đến `Dim_Coupon` |
| `campaign_key` | FK đến `Dim_Campaign` |
| `redemption_date_key` | FK đến `Dim_Date` |
| `redemption_record_count` | Giá trị 1 để đếm bản ghi đổi coupon |
| `etl_batch_id` | Mã lần nạp |
| `loaded_at` | Thời điểm nạp |

Ràng buộc duy nhất:

`household_key + coupon_key + campaign_key + redemption_date_key`

### 6.3. Giới hạn phân tích

- Không có `product_key`, `store_key` hoặc `basket_id` vì nguồn
  đổi coupon không cung cấp các trường này.
- Không tự gán doanh số cho một lần đổi coupon.
- Một coupon có thể áp dụng cho nhiều sản phẩm.
- Coupon có sản phẩm FMCG đủ điều kiện không chứng minh lần đổi
  coupon đó thực tế dùng cho sản phẩm FMCG.
- `redemption_record_count` đếm bản ghi quan sát được trong nguồn.

## 7. Các bảng Dimension

| Bảng | Grain và khóa nghiệp vụ | Thuộc tính chính |
|---|---|---|
| `Dim_Product` | Một sản phẩm; `product_id` | `manufacturer_id`, `department`, `brand`, `product_category`, `product_type`, `package_size`, `scope_status`, `scope_rule_version`, `source_lookup_missing_flag` |
| `Dim_Household` | Một hộ gia đình; `household_id` | `age`, `income`, `home_ownership`, `marital_status`, `household_size`, `household_comp`, `kids_count`, `demographics_available_flag` |
| `Dim_Store` | Một cửa hàng; `store_id` | Mã cửa hàng nguồn |
| `Dim_Date` | Một ngày; `full_date` | Ngày, tháng, quý, năm, thứ trong tuần |
| `Dim_Week` | Một tuần của lịch nguồn; `source_calendar_id + source_week` | `week_start_date`, `week_end_date`, `coverage_start_date`, `coverage_end_date`, `is_partial_coverage` |
| `Dim_Campaign` | Một chiến dịch; `campaign_id` | `campaign_type`, `start_date`, `end_date` |
| `Dim_Coupon` | Một coupon trong một chiến dịch; `campaign_id + coupon_upc` | Mã coupon và mã chiến dịch nguồn |

Mỗi Dimension có khóa chính tương ứng:
`product_key`, `household_key`, `store_key`, `date_key`, `week_key`,
`campaign_key`, `coupon_key`.

### 7.1. Sản phẩm

- Giữ toàn bộ danh mục để hỗ trợ liên kết coupon và phân loại phạm vi.
- Mã sản phẩm có trong các bảng nguồn nhưng thiếu lookup được tạo
  bản ghi riêng, giữ mã nguồn và bật `source_lookup_missing_flag`.
- Các mã thiếu lookup được giữ ở trạng thái REVIEW, không tự đưa
  vào Fact bán hàng FMCG.
- `brand` là phân loại nhãn riêng/nhãn quốc gia, không phải tên thương hiệu.
- Không tạo tên sản phẩm hoặc đơn vị đo khi nguồn không cung cấp.

### 7.2. Hộ gia đình

- Đây là hộ gia đình, không phải khách hàng cá nhân.
- Lấy hợp các mã hộ từ giao dịch, chiến dịch, đổi coupon và demographics.
- Hộ có mã nhưng thiếu demographics vẫn có bản ghi Dimension riêng.
- Không gom tất cả hộ thiếu demographics vào một khóa Unknown.

### 7.3. Cửa hàng

Lấy hợp mã cửa hàng từ giao dịch và khuyến mãi.

Nguồn hiện tại không có bảng mô tả địa lý cửa hàng. Không tự bổ sung
tên cửa hàng, thành phố, bang hoặc khu vực.

### 7.4. Ngày và tuần

- Ngày giao dịch được xác định theo `America/New_York`.
- `Dim_Date` bao phủ toàn bộ khoảng ngày cần dùng cho bán hàng,
  chiến dịch và đổi coupon, kể cả ngày không có giao dịch.
- Không giới hạn lịch chỉ ở năm 2017 nếu chiến dịch có ngày ngoài năm này.
- Với giao dịch hiện tại, `source_week` khớp hoàn toàn công thức
  `as.integer(format(local_date, "%W")) + 1L`.
- Không thay tuần nguồn bằng tuần ISO.

Lịch nguồn được đặt mã `CJ_2017`:

- Tuần 1 có khoảng lịch 26/12/2016–01/01/2017;
  phần nằm trong phạm vi giao dịch là 01/01/2017.
- Tuần 2 có khoảng lịch 02/01/2017–08/01/2017.
- Tuần 53 có khoảng lịch 25/12/2017–31/12/2017.
- Ngày 25/12/2017 không có giao dịch nhưng vẫn thuộc lịch tuần 53.
- Không xác định ngày bắt đầu/kết thúc tuần bằng MIN/MAX ngày có bán.

`Fact_Sales` lưu cả `date_key` và `week_key`. ETL kiểm tra chúng
nhất quán với lịch nguồn. Không bắt buộc mọi ngày của chiến dịch
ngoài phạm vi giao dịch phải thuộc một tuần `CJ_2017`.

### 7.5. Coupon và chiến dịch

`Dim_Coupon` dùng khóa nghiệp vụ ghép `campaign_id + coupon_upc`
để không giả định mã coupon duy nhất trên mọi chiến dịch.

Trong Fact đổi coupon, `coupon_key` và `campaign_key` phải cùng
chỉ đến một chiến dịch nhất quán.

## 8. Các bảng liên kết

### 8.1. Bridge_Campaign_Household

Nguồn: `campaigns.rda`.

Một dòng là một cặp chiến dịch–hộ gia đình có trong nguồn.

| Cột | Vai trò |
|---|---|
| `campaign_key` | FK đến `Dim_Campaign` |
| `household_key` | FK đến `Dim_Household` |

Khóa chính ghép: `campaign_key + household_key`.

Bảng này cũng có thể được xem là Fact không có measure, ghi nhận
việc hộ gia đình thuộc danh sách của chiến dịch.

### 8.2. Bridge_Coupon_Product

Nguồn: `coupons.rda`.

Một dòng là một sản phẩm đủ điều kiện sử dụng một coupon trong
một chiến dịch.

| Cột | Vai trò |
|---|---|
| `coupon_key` | FK đến `Dim_Coupon`, đã xác định chiến dịch |
| `product_key` | FK đến `Dim_Product` |

Khóa chính ghép: `coupon_key + product_key`.

Loại bản ghi trùng hoàn toàn khi tạo liên kết; giữ bản gốc tại Staging.

Không nhân bản Fact đổi coupon cho tất cả sản phẩm đủ điều kiện.
Khi lọc coupon theo sản phẩm, ưu tiên EXISTS hoặc tập khóa phân biệt
để tránh đếm một lần đổi nhiều lần.

## 9. Chính sách cập nhật Dimension

Giai đoạn đầu sử dụng cập nhật kiểu Type 1 cho thuộc tính mô tả,
do nguồn hiện tại không cung cấp lịch sử thay đổi thuộc tính.

- Giữ nguyên bản nguồn tại Raw và Staging.
- Không tạo lịch sử SCD Type 2 giả định.
- Lưu phiên bản quy tắc phân loại FMCG.
- Nếu thay đổi phiên bản phân loại, phải nạp lại hoặc đối soát lại
  các Fact chịu ảnh hưởng; không chỉ đổi nhãn trong Dimension.

Khóa Unknown chỉ dùng khi thật sự không xác định được mã.
Mã nguồn có giá trị nhưng thiếu thuộc tính phải được giữ thành
bản ghi Dimension riêng.

## 10. Nguyên tắc truy vấn và kiểm soát

- Mỗi quan hệ Dimension–Fact là một–nhiều.
- Không nối trực tiếp Fact bán hàng với Fact đổi coupon để tính doanh số.
- Không nối bán hàng qua bảng chiến dịch–hộ gia đình rồi cộng doanh số
  cho từng chiến dịch mà không có quy tắc phân bổ.
- Khi so sánh các Fact, tổng hợp về cùng mức chi tiết trước khi kết hợp.
- Bảng khuyến mãi theo tuần phải duy nhất trên sản phẩm–cửa hàng–tuần.
- Không có `Dim_Channel` vì dữ liệu hiện tại không cung cấp kênh bán.
- Chưa cần `Dim_Promotion` riêng: trạng thái quảng cáo/trưng bày
  được lưu trong `Fact_Promotion_Weekly`.
- Hiệu quả khuyến mãi được phân tích theo hướng mô tả và so sánh,
  không kết luận quan hệ nhân quả.

## 11. Điều kiện chấp nhận mô hình

- Không trùng khóa nghiệp vụ của từng Fact và bảng liên kết.
- Mọi khóa ngoại ánh xạ được đến Dimension.
- Fact bán hàng v1.3 có 1.271.042 dòng.
- Tổng `sales_value` của Fact bán hàng là 3.419.948,46 USD.
- Nối thông tin khuyến mãi không làm tăng số dòng hoặc doanh số bán hàng.
- Các dòng số lượng bằng 0 vẫn được giữ trong Fact.
- Việc loại dòng khỏi KPI giá được thực hiện tại lớp tính KPI.
- Các công thức giá chưa xác minh chưa trở thành measure chính thức.