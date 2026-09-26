# Thiết kế vùng Staging

## 1. Mục đích

Schema `staging` tiếp nhận đầy đủ tám bảng nguồn Complete Journey,
phục vụ kiểm tra chất lượng, đối soát và nạp kho dữ liệu.

Nguyên tắc:

- Không lọc FMCG tại bước nạp Staging.
- Không xóa trùng, điền thiếu hoặc sửa giá trị nghiệp vụ tại Staging.
- Giữ mã nguồn, giá trị thiếu và các bản ghi bất thường.
- Chuyển kiểu có kiểm soát, không âm thầm làm tròn hoặc cắt chuỗi.
- Mỗi dòng có thông tin file nguồn, vị trí dòng và lần nạp.
- File RDA/RDS trong Raw là bản gốc dùng đối chiếu.
- Các CSV xuất để xem không được nạp đồng thời với file R nguồn.

Staging giữ giá trị dữ liệu đã đọc từ nguồn. Các thuộc tính riêng của R
như factor levels và nhãn kiểu dữ liệu không được bảo toàn hoàn toàn
trong bảng SQL; file Raw tiếp tục là bản tham chiếu đầy đủ.

## 2. Danh sách bảng

| Bảng Staging | File nguồn | Số dòng nguồn hiện tại |
|---|---|---:|
| `stg_transactions` | `transactions.rds` | 1.469.307 |
| `stg_promotions` | `promotions.rds` | 20.940.529 |
| `stg_products` | `products.rda` | 92.331 |
| `stg_demographics` | `demographics.rda` | 801 |
| `stg_campaigns` | `campaigns.rda` | 6.589 |
| `stg_campaign_descriptions` | `campaign_descriptions.rda` | 27 |
| `stg_coupons` | `coupons.rda` | 116.204 |
| `stg_coupon_redemptions` | `coupon_redemptions.rda` | 2.102 |

Đây là mốc đối soát của bản nguồn hiện tại, không ghi cứng để áp dụng
cho mọi phiên bản dữ liệu trong tương lai.

## 3. Cột kỹ thuật dùng chung

Tám bảng đều bổ sung các cột sau:

| Cột | Kiểu dự kiến | Ý nghĩa |
|---|---|---|
| `staging_row_id` | `BIGINT GENERATED ALWAYS AS IDENTITY` | Khóa chính kỹ thuật |
| `etl_batch_id` | `BIGINT` | Lần nạp, tham chiếu `audit.etl_batch` |
| `source_file_name` | `TEXT` | Tên file nguồn |
| `source_object_name` | `TEXT` | Tên đối tượng trong RDA; NULL nếu không áp dụng |
| `source_row_number` | `BIGINT` | Thứ tự dòng trong đối tượng nguồn, bắt đầu từ 1 |
| `loaded_at` | `TIMESTAMPTZ` | Thời điểm dòng được nạp |

Các cột kỹ thuật bắt buộc có giá trị, ngoại trừ `source_object_name`.

Ràng buộc duy nhất trong mỗi bảng:

`etl_batch_id + source_file_name + source_row_number`

Thiết kế hiện tại giả định mỗi file nguồn chứa một bảng.
Nếu file RDA xuất hiện nhiều đối tượng, pipeline phải dừng để cập nhật
ánh xạ; không tự chọn đối tượng đầu tiên.

Không đặt UNIQUE theo khóa nghiệp vụ tại Staging để có thể lưu và
kiểm tra bản ghi trùng của nguồn.

## 4. Quy ước kiểu dữ liệu

- Mã định danh dùng `TEXT` để bảo toàn biểu diễn mã.
- Thuộc tính phân nhóm dùng `TEXT`; factor của R được đọc thành nhãn.
- Số lượng và tiền dùng `NUMERIC` chưa giới hạn phần thập phân tại Staging.
- Tuần dùng `INTEGER`, sau khi kiểm tra giá trị nguồn thực sự là số nguyên.
- Ngày dùng `DATE`.
- Thời điểm dùng `TIMESTAMPTZ`.
- Giá trị NA của nguồn ánh xạ thành SQL NULL.
- Không tự đổi chuỗi rỗng thành NULL, không trim hoặc viết hoa dữ liệu nguồn.
- Các cột nghiệp vụ cho phép NULL tại Staging để giữ được dữ liệu thiếu;
  yêu cầu bắt buộc được kiểm tra bằng quy tắc chất lượng.

Khi chuyển số thực từ R sang NUMERIC, sử dụng biểu diễn thập phân
đủ độ chính xác và kiểm tra đối soát. Không nhân 100 rồi làm tròn
ngay trong bước nạp Staging.

## 5. Thiết kế tám bảng nguồn

Các bảng dưới đây chỉ liệt kê cột nghiệp vụ.
Cột kỹ thuật tại mục 3 được bổ sung cho tất cả các bảng.

### 5.1. staging.stg_transactions

Một dòng tương ứng một dòng giao dịch nguồn.

| Cột | Kiểu dự kiến |
|---|---|
| `household_id` | `TEXT` |
| `store_id` | `TEXT` |
| `basket_id` | `TEXT` |
| `product_id` | `TEXT` |
| `quantity` | `NUMERIC` |
| `sales_value` | `NUMERIC` |
| `retail_disc` | `NUMERIC` |
| `coupon_disc` | `NUMERIC` |
| `coupon_match_disc` | `NUMERIC` |
| `week` | `INTEGER` |
| `transaction_timestamp` | `TIMESTAMPTZ` |

Khóa nghiệp vụ cần kiểm tra: `basket_id + product_id`.

Quy tắc:

- Nạp toàn bộ 1.469.307 dòng của bản nguồn hiện tại.
- Giữ cả IN_SCOPE, OUT_OF_SCOPE và REVIEW.
- Giữ số lượng bằng 0, doanh số bằng 0 và các bất thường giảm giá.
- Không tính giá trước giảm hoặc tiền khách thực trả tại Staging.

Múi giờ nguồn `America/New_York` được lưu trong metadata lần nạp.
`TIMESTAMPTZ` giữ thời điểm tuyệt đối nhưng không giữ tên múi giờ gốc.

Khi tạo ngày nghiệp vụ ở bước biến đổi, sử dụng:

`(transaction_timestamp AT TIME ZONE 'America/New_York')::date`

Không lấy ngày theo múi giờ mặc định của máy hoặc phiên kết nối.

### 5.2. staging.stg_promotions

Một dòng tương ứng một dòng quảng cáo/trưng bày nguồn.

| Cột | Kiểu dự kiến |
|---|---|
| `product_id` | `TEXT` |
| `store_id` | `TEXT` |
| `display_location` | `TEXT` |
| `mailer_location` | `TEXT` |
| `week` | `INTEGER` |

Quy tắc:

- Giữ nguyên các mã như `0`, `A` và các mã vị trí khác.
- Không đổi trực tiếp thành BOOLEAN tại Staging.
- Không gom theo sản phẩm–cửa hàng–tuần tại bước nạp.
- Không đặt UNIQUE trên tổ hợp sản phẩm–cửa hàng–tuần.
- Việc gom trạng thái được thực hiện khi tạo `Fact_Promotion_Weekly`.

### 5.3. staging.stg_products

Một dòng tương ứng một dòng danh mục sản phẩm nguồn.

| Cột | Kiểu dự kiến |
|---|---|
| `product_id` | `TEXT` |
| `manufacturer_id` | `TEXT` |
| `department` | `TEXT` |
| `brand` | `TEXT` |
| `product_category` | `TEXT` |
| `product_type` | `TEXT` |
| `package_size` | `TEXT` |

Khóa nghiệp vụ cần kiểm tra: `product_id`.

Quy tắc:

- Giữ đủ danh mục, kể cả sản phẩm không phát sinh giao dịch.
- Giữ nguyên nhãn `brand`.
- Không suy diễn đơn vị số lượng từ `package_size`.
- Không chèn sản phẩm Unknown hoặc sản phẩm thiếu lookup vào bảng
  nguồn này; các bản ghi bổ sung được tạo tại lớp Dimension.

### 5.4. staging.stg_demographics

Một dòng tương ứng một hộ có thông tin nhân khẩu học trong nguồn.

| Cột | Kiểu dự kiến |
|---|---|
| `household_id` | `TEXT` |
| `age` | `TEXT` |
| `income` | `TEXT` |
| `home_ownership` | `TEXT` |
| `marital_status` | `TEXT` |
| `household_size` | `TEXT` |
| `household_comp` | `TEXT` |
| `kids_count` | `TEXT` |

Khóa nghiệp vụ cần kiểm tra: `household_id`.

Các thuộc tính được lưu theo nhãn nguồn, bao gồm nhóm tuổi,
nhóm thu nhập và nhóm kích thước hộ.

Không đổi nhóm tuổi thành tuổi chính xác hoặc nhóm thu nhập thành
một giá trị thu nhập giả định.

Không bổ sung các hộ thiếu demographics vào bảng Staging này.

### 5.5. staging.stg_campaigns

Một dòng tương ứng một liên kết chiến dịch–hộ gia đình trong nguồn.

| Cột | Kiểu dự kiến |
|---|---|
| `campaign_id` | `TEXT` |
| `household_id` | `TEXT` |

Khóa nghiệp vụ cần kiểm tra: `campaign_id + household_id`.

Không tự tạo ngày gửi, ngày nhận hoặc trạng thái phản hồi vì nguồn
không cung cấp các trường này.

### 5.6. staging.stg_campaign_descriptions

Một dòng tương ứng một chiến dịch.

| Cột | Kiểu dự kiến |
|---|---|
| `campaign_id` | `TEXT` |
| `campaign_type` | `TEXT` |
| `start_date` | `DATE` |
| `end_date` | `DATE` |

Khóa nghiệp vụ cần kiểm tra: `campaign_id`.

Giữ các ngày ngoài năm 2017. Không cắt thời gian chiến dịch theo
khoảng thời gian của giao dịch bán hàng.

### 5.7. staging.stg_coupons

Một dòng tương ứng một liên kết coupon–sản phẩm–chiến dịch trong nguồn.

| Cột | Kiểu dự kiến |
|---|---|
| `coupon_upc` | `TEXT` |
| `product_id` | `TEXT` |
| `campaign_id` | `TEXT` |

Tổ hợp cần kiểm tra:

`campaign_id + coupon_upc + product_id`

Giữ toàn bộ 116.204 dòng nguồn, bao gồm bản ghi trùng.

Việc loại trùng để tạo `Bridge_Coupon_Product` được thực hiện
ở bước biến đổi, không thực hiện khi nạp Staging.

### 5.8. staging.stg_coupon_redemptions

Một dòng tương ứng một bản ghi đổi coupon trong nguồn.

| Cột | Kiểu dự kiến |
|---|---|
| `household_id` | `TEXT` |
| `coupon_upc` | `TEXT` |
| `campaign_id` | `TEXT` |
| `redemption_date` | `DATE` |

Tổ hợp cần kiểm tra:

`household_id + coupon_upc + campaign_id + redemption_date`

Không tự thêm mã sản phẩm, cửa hàng hoặc giỏ hàng vào bản ghi đổi coupon.

## 6. Metadata và nhật ký nạp

### 6.1. audit.etl_batch

Ghi nhận một lần nạp toàn bộ bộ dữ liệu.

| Cột | Ý nghĩa |
|---|---|
| `etl_batch_id` | Khóa chính của lần nạp |
| `dataset_name` | Tên bộ dữ liệu |
| `source_manifest_hash` | Hash đại diện cho danh sách file và SHA-256 của từng file |
| `pipeline_version` | Phiên bản chương trình nạp |
| `started_at` | Thời điểm bắt đầu |
| `finished_at` | Thời điểm kết thúc |
| `status` | RUNNING, SUCCESS hoặc FAILED |
| `error_message` | Thông báo lỗi nếu có |

### 6.2. audit.etl_file_load

Ghi nhận kết quả nạp từng file trong một batch.

| Cột | Ý nghĩa |
|---|---|
| `etl_batch_id` | Lần nạp |
| `source_file_name` | Tên file |
| `source_file_sha256` | SHA-256 của file gốc |
| `source_object_name` | Tên đối tượng R nếu có |
| `target_table` | Bảng Staging đích |
| `source_row_count` | Số dòng đọc từ nguồn |
| `loaded_row_count` | Số dòng đã nạp |
| `source_timezone` | Múi giờ nguồn nếu có |
| `status` | Trạng thái nạp file |
| `error_message` | Chi tiết lỗi |

Khóa duy nhất: `etl_batch_id + source_file_name`.

Các kết quả kiểm tra và tổng đối soát được lưu trong schema `audit`,
không ghi đè giá trị nghiệp vụ trong Staging.

## 7. Quy trình nạp

1. Kiểm tra đủ tám file nguồn.
2. Tính SHA-256 và lập manifest.
3. Kiểm tra cấu trúc cột và kiểu dữ liệu.
4. Tạo bản ghi `audit.etl_batch` ở trạng thái RUNNING.
5. Đọc lần lượt từng file, gắn số dòng nguồn và metadata.
6. Nạp từng bảng bằng cơ chế bulk load.
7. Đối soát số dòng, số giá trị thiếu và các tổng số liệu.
8. Ghi kết quả từng file.
9. Chỉ đánh dấu batch SUCCESS khi đủ tám bảng đã nạp và đối soát đạt.

Có thể chia dữ liệu thành nhiều lô ghi để giảm bộ nhớ khi nạp PostgreSQL.
Việc chia lô ghi không có nghĩa file RDS được đọc từng phần; bộ đọc
vẫn có thể phải nạp toàn bộ đối tượng R vào RAM.

## 8. Chạy lại và quản lý phiên bản

- Mỗi batch là một bản chụp đầy đủ của tám bảng nguồn.
- Nếu manifest và phiên bản pipeline đã có batch SUCCESS,
  mặc định bỏ qua việc nạp lại.
- Nếu thử lại batch FAILED, xóa và nạp lại dữ liệu của bảng bị lỗi
  trong chính batch đó bằng một transaction.
- Không xóa dữ liệu của batch SUCCESS cũ khi thử lại.
- File nguồn thay đổi hoặc cần tái xử lý có chủ đích thì tạo batch mới.
- Các bước tạo DW phải chỉ định rõ một batch SUCCESS.
- Không đọc gộp tất cả batch vì sẽ nhân bản dữ liệu.

Không sử dụng “batch mới nhất của từng bảng” riêng lẻ để ghép dữ liệu,
vì có thể trộn các phiên bản nguồn khác nhau.

## 9. Kiểm tra chất lượng và đối soát

### 9.1. Điều kiện nạp thành công

- Đủ tám bảng thuộc cùng batch.
- Đúng cấu trúc cột đã khai báo.
- Không có lỗi chuyển kiểu bị bỏ qua.
- Số dòng nguồn bằng số dòng đã nạp của từng bảng.
- Số giá trị NULL theo cột khớp với nguồn.
- Tổng số lượng và từng trường tiền khớp với nguồn theo quy tắc
  độ chính xác đã công bố.
- Thời điểm giao dịch không bị thay đổi khi chuyển đổi múi giờ.
- Không trùng định danh kỹ thuật của dòng nguồn trong cùng batch.

Nếu không chuyển kiểu được một giá trị, đánh dấu nạp thất bại và ghi
file, dòng, cột gây lỗi. Không thay bằng NULL để tiếp tục âm thầm.

### 9.2. Bất thường nghiệp vụ

Các trường hợp dưới đây được ghi nhận nhưng vẫn giữ tại Staging:

- Khóa nghiệp vụ trùng.
- Khóa sản phẩm thiếu trong lookup.
- Thiếu thuộc tính nhân khẩu học.
- Số lượng bằng 0.
- Coupon lớn hơn doanh số.
- Nhiều trạng thái khuyến mãi cho cùng sản phẩm–cửa hàng–tuần.
- Mã quảng cáo hoặc trưng bày chưa nhận diện.

Việc quyết định bản ghi nào đủ điều kiện nạp DW được thực hiện
ở bước biến đổi theo quy tắc đã công bố.

## 10. Phân loại FMCG và dữ liệu dẫn xuất

`product_scope.csv` là kết quả phân loại nội bộ, không thuộc tám bảng
nguồn Complete Journey.

- Giữ phiên bản và hash của kết quả phân loại dùng cho mỗi lần nạp DW.
- Không ghi đè `department`, `product_category` hoặc `product_type`
  của nguồn bằng nhãn đã chuẩn hóa.
- Việc chuẩn hóa chuỗi, phân loại phạm vi, tạo cờ chất lượng,
  gom khuyến mãi và loại trùng liên kết coupon diễn ra sau Staging.
- Không loại OUT_OF_SCOPE hoặc REVIEW khỏi Staging.

## 11. Phạm vi triển khai hiện tại

Tài liệu này chốt thiết kế logic của vùng Staging.

Các phần sẽ được thực hiện tiếp:

- Source-to-target mapping.
- DDL cho schema `staging` và `audit`.
- Chương trình nạp tám bảng.
- Kiểm tra khả năng chạy lại và đối soát.