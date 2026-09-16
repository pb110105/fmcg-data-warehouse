# Data Dictionary dữ liệu nguồn

## 1. Quy ước

- `Business key`: khóa nghiệp vụ có trong dữ liệu nguồn.
- `Measure`: chỉ số có thể tổng hợp.
- `Attribute`: thuộc tính mô tả.
- UPC và MSA được lưu dưới dạng chuỗi trong kho dữ liệu để bảo toàn ý nghĩa mã định danh.
- Kiểu dữ liệu đích là đề xuất ban đầu; DDL chi tiết được hoàn thiện ở giai đoạn thiết kế.

## 2. Sheet `dh Transaction Data`

| Cột nguồn | Kiểu quan sát | Kiểu đích dự kiến | Cho phép NULL | Vai trò | Ý nghĩa và quy tắc |
|---|---|---|---|---|---|
| `WEEK_END_DATE` | Date/Datetime | `DATE` | Không | Business key | Ngày kết thúc tuần; phải chuyển đổi được sang ngày hợp lệ |
| `STORE_NUM` | Integer | `INTEGER` | Không | Business key, FK | Mã cửa hàng; liên kết với `STORE_ID` của bảng cửa hàng |
| `UPC` | Integer | `VARCHAR(14)` | Không | Business key, FK | Mã sản phẩm; chuyển sang chuỗi trước khi nạp |
| `UNITS` | Integer | `INTEGER` | Không | Measure | Số lượng bán; giá trị phải lớn hơn hoặc bằng 0 |
| `VISITS` | Integer | `INTEGER` | Không | Measure | Số lượt mua có chứa sản phẩm; phải lớn hơn hoặc bằng 0 |
| `HHS` | Integer | `INTEGER` | Không | Measure | Số hộ gia đình mua sản phẩm; phải lớn hơn hoặc bằng 0 |
| `SPEND` | Decimal | `NUMERIC(14,2)` | Không | Measure | Doanh số bằng USD; phải lớn hơn hoặc bằng 0 |
| `PRICE` | Decimal | `NUMERIC(10,2)` | Có | Measure | Giá thực tế tại kệ; thiếu 23 bản ghi |
| `BASE_PRICE` | Decimal | `NUMERIC(10,2)` | Có | Measure | Giá cơ sở; thiếu 185 bản ghi |
| `FEATURE` | Integer | `SMALLINT` hoặc `BOOLEAN` | Không | Promotion flag | Có xuất hiện trong tờ quảng cáo: 1 có, 0 không |
| `DISPLAY` | Integer | `SMALLINT` hoặc `BOOLEAN` | Không | Promotion flag | Có trưng bày tại cửa hàng: 1 có, 0 không |
| `TPR_ONLY` | Integer | `SMALLINT` hoặc `BOOLEAN` | Không | Promotion flag | Chỉ giảm giá tạm thời tại kệ: 1 có, 0 không |

Khóa tự nhiên của sheet là tổ hợp `WEEK_END_DATE + STORE_NUM + UPC`. Khảo sát không phát hiện bản ghi trùng trên tổ hợp này.

## 3. Sheet `dh Products Lookup`

| Cột nguồn | Kiểu quan sát | Kiểu đích dự kiến | Cho phép NULL | Vai trò | Ý nghĩa và quy tắc |
|---|---|---|---|---|---|
| `UPC` | Integer | `VARCHAR(14)` | Không | Business key | Mã sản phẩm duy nhất |
| `DESCRIPTION` | Text | `VARCHAR(255)` | Không | Attribute | Mô tả sản phẩm |
| `MANUFACTURER` | Text | `VARCHAR(100)` | Không | Attribute | Nhà sản xuất |
| `CATEGORY` | Text | `VARCHAR(100)` | Không | Attribute | Ngành hàng sản phẩm |
| `SUB_CATEGORY` | Text | `VARCHAR(150)` | Không | Attribute | Tiểu ngành hàng |
| `PRODUCT_SIZE` | Text | `VARCHAR(50)` | Không | Attribute | Kích thước hoặc quy cách đóng gói; giữ nguyên chuỗi nguồn |

`UPC` có 58 giá trị phân biệt và không có khóa trùng. Ba sản phẩm không phát sinh bán hàng vẫn được giữ trong `Dim_Product` để phản ánh đầy đủ danh mục nguồn.

## 4. Sheet `dh Store Lookup`

| Cột nguồn | Kiểu quan sát | Kiểu đích dự kiến | Cho phép NULL | Vai trò | Ý nghĩa và quy tắc |
|---|---|---|---|---|---|
| `STORE_ID` | Integer | `INTEGER` | Không | Business key | Mã cửa hàng; tương ứng với `STORE_NUM` của bảng giao dịch |
| `STORE_NAME` | Text | `VARCHAR(150)` | Không | Attribute | Tên cửa hàng |
| `ADDRESS_CITY_NAME` | Text | `VARCHAR(100)` | Không | Attribute | Thành phố |
| `ADDRESS_STATE_PROV_CODE` | Text | `CHAR(2)` | Không | Attribute | Mã bang: `IN`, `KY`, `OH` hoặc `TX` |
| `MSA_CODE` | Integer | `VARCHAR(10)` | Không | Attribute | Mã Metropolitan Statistical Area; lưu dưới dạng chuỗi |
| `SEG_VALUE_NAME` | Text | `VARCHAR(30)` | Không | Attribute | Phân khúc cửa hàng: `VALUE`, `MAINSTREAM` hoặc `UPSCALE` |
| `PARKING_SPACE_QTY` | Decimal | `INTEGER` | Có | Attribute | Số chỗ đậu xe; thiếu 52/79 dòng lookup |
| `SALES_AREA_SIZE_NUM` | Integer | `INTEGER` | Không | Attribute | Diện tích bán hàng theo feet vuông |
| `AVG_WEEKLY_BASKETS` | Decimal | `NUMERIC(14,6)` | Không | Attribute | Số giỏ hàng trung bình hàng tuần của cửa hàng |

`STORE_ID` có 77 giá trị phân biệt trên 79 dòng. Hai mã `4503` và `17627` bị mâu thuẫn phân khúc và phải được xử lý trước khi tạo `Dim_Store`.

## 5. Khác biệt giữa Glossary và sheet thực tế

| Glossary | Sheet thực tế | Cách hiểu trong hệ thống |
|---|---|---|
| `STORE_NUM` trong store lookup | `STORE_ID` | Hai cột là cùng mã cửa hàng và được dùng để join |
| `STORE_APPEAL` | `SEG_VALUE_NAME` | `SEG_VALUE_NAME` là tên cột thực tế biểu diễn phân khúc/định vị cửa hàng |
| Không mô tả `STORE_NAME` | Có `STORE_NAME` | Giữ làm thuộc tính mô tả của `Dim_Store` |

ETL phải ưu tiên tên cột thực tế trong workbook, đồng thời ghi nhận ánh xạ trên trong tài liệu thiết kế nguồn–đích.

