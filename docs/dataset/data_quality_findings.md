# Đánh giá sơ bộ chất lượng dữ liệu

## 1. Nguyên tắc xử lý

- Giữ nguyên dữ liệu nguồn trong vùng Raw và Staging.
- Không xóa bản ghi chỉ vì giá trị bất thường nếu chưa chứng minh được đó là lỗi.
- Tạo cờ chất lượng dữ liệu để có thể truy vết và lọc khi phân tích.
- Tách lỗi làm hỏng khóa hoặc phép join khỏi các bất thường nghiệp vụ chỉ cần cảnh báo.
- Đối soát số dòng và tổng các measure sau mỗi bước nạp.

## 2. Kết quả kiểm tra tổng quát

| Kiểm tra | Kết quả |
|---|---:|
| Bản ghi giao dịch | 524.950 |
| Trùng khóa `WEEK_END_DATE + STORE_NUM + UPC` | 0 |
| Trùng toàn bộ dòng giao dịch | 0 |
| Khóa cửa hàng không khớp lookup | 0 |
| Khóa sản phẩm không khớp lookup | 0 |
| Giá trị âm trong các measure | 0 |
| Cờ khuyến mãi ngoài miền `{0,1}` | 0 |
| Chênh lệch `SPEND` và `UNITS × PRICE` lớn hơn 0,01 USD trên dòng có giá | 0 |
| Khoảng cách giữa các tuần khác bảy ngày | 0 |

## 3. Vấn đề và quy tắc xử lý dự kiến

| Mã | Vấn đề | Số dòng | Mức độ | Quy tắc dự kiến |
|---|---|---:|---|---|
| DQ01 | `PRICE` bị thiếu | 23 | Trung bình | Giữ nguyên `PRICE` nguồn; tạo `price_clean`. Với 18 dòng có `UNITS > 0`, tính `price_clean = SPEND / UNITS`; kết quả thu được bằng 0. Năm dòng có `UNITS = 0` giữ `price_clean = NULL`. Gắn `price_imputed_flag` cho 18 dòng được tính lại và `price_missing_flag` cho năm dòng không thể tính |
| DQ02 | `BASE_PRICE` bị thiếu | 185 | Trung bình | Không tự suy diễn. Giữ NULL, gắn `base_price_missing_flag` và loại khỏi KPI giảm giá cần giá cơ sở |
| DQ03 | `PRICE > BASE_PRICE` | 6.047 | Cảnh báo | Giữ nguyên; gắn `price_above_base_flag`. Không ép mức giảm giá về 0 vì giá cao hơn giá cơ sở là thông tin quan sát được |
| DQ04 | `UNITS < VISITS` | 2.309 | Cảnh báo | Giữ nguyên; gắn `units_lt_visits_flag`. Không dùng riêng hiện tượng này để xóa dòng |
| DQ05 | `UNITS/VISITS > 3` | 287 | Cảnh báo | Giữ nguyên; gắn `high_units_per_visit_flag` để phân tích độ nhạy |
| DQ06 | `VISITS/HHS > 3` | 293 | Cảnh báo | Giữ nguyên; gắn `high_visits_per_hh_flag` để phân tích độ nhạy |
| DQ07 | `UNITS = 0` | 5 | Cảnh báo | Giữ nguyên vì vẫn có `VISITS` và `HHS`; đánh dấu để không chia cho 0 trong KPI giá |
| DQ08 | `SPEND = 0` | 24 | Cảnh báo | Giữ nguyên; kiểm tra cùng `UNITS` và `PRICE`; không xem là lỗi âm |
| DQ09 | `PRICE = 0` nhưng có bán | 1 | Cảnh báo | Giữ nguyên và gắn cờ; có thể phản ánh sản phẩm miễn phí hoặc giá đặc biệt |
| DQ10 | Trùng mã cửa hàng và mâu thuẫn phân khúc | 4 dòng lookup, 2 mã | Nghiêm trọng | Tạo đúng một bản ghi cho mỗi `STORE_ID`; gán `SEG_VALUE_NAME = 'UNKNOWN_CONFLICT'` cho `4503` và `17627`; lưu giá trị nguồn trong Staging |
| DQ11 | `PARKING_SPACE_QTY` bị thiếu | 52/79 dòng lookup | Thấp | Giữ NULL; không điền 0 vì 0 có ý nghĩa khác với chưa biết |
| DQ12 | Ba sản phẩm lookup không có giao dịch | 3 sản phẩm | Thông tin | Vẫn nạp vào `Dim_Product`; không tạo dòng Fact nếu không có bán hàng |
| DQ13 | Tên cột khóa cửa hàng không đồng nhất | Metadata | Trung bình | Ánh xạ `STORE_NUM` của giao dịch với `STORE_ID` của lookup trong source-to-target mapping |
| DQ14 | Glossary dùng `STORE_APPEAL`, sheet dùng `SEG_VALUE_NAME` | Metadata | Thấp | Dùng `SEG_VALUE_NAME` làm cột nguồn thực tế và ghi chú ánh xạ |

## 4. Chi tiết xung đột cửa hàng

| STORE_ID | Tên cửa hàng | Bang | Phân khúc nguồn |
|---:|---|---|---|
| 4503 | ROCKWALL | TX | `MAINSTREAM`, `UPSCALE` |
| 17627 | FLOWER MOUND | TX | `MAINSTREAM`, `UPSCALE` |

Hai cửa hàng liên quan đến 13.693 dòng giao dịch, tương đương khoảng 2,61% Fact. Join lookup chưa xử lý sẽ biến 13.693 dòng này thành 27.386 dòng và làm tăng sai doanh số, sản lượng cùng các KPI liên quan.

## 5. Cờ chất lượng dữ liệu dự kiến

Bảng xử lý trung gian hoặc Fact có thể lưu các cờ sau:

- `price_imputed_flag`.
- `price_missing_flag`.
- `base_price_missing_flag`.
- `price_above_base_flag`.
- `units_lt_visits_flag`.
- `high_units_per_visit_flag`.
- `high_visits_per_hh_flag`.
- `store_segment_conflict_flag`.

Chi tiết lỗi có thể được ghi trong schema `audit`; các cờ phục vụ lọc và đối soát, không thay thế dữ liệu nguồn.

## 6. Điều kiện chấp nhận trước khi nạp kho dữ liệu

- Khóa tự nhiên của Fact không trùng.
- Mọi `UPC` và `STORE_NUM` phải ánh xạ được sang bảng chiều hoặc bản ghi Unknown.
- Mỗi `STORE_ID` chỉ tạo một dòng hiện hành trong `Dim_Store`.
- Các cờ khuyến mãi chỉ nhận 0 hoặc 1.
- Không có measure âm.
- Các phép chia phải dùng `NULLIF` hoặc kiểm tra mẫu số bằng 0.
- Tổng số dòng, `UNITS` và `SPEND` phải được đối soát giữa Staging và Fact theo quy tắc xử lý đã công bố.

