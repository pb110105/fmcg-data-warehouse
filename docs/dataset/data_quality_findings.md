# Đánh giá sơ bộ chất lượng dữ liệu

## 1. Phạm vi và nguyên tắc xử lý

Tài liệu ghi nhận kết quả kiểm tra tám bảng Complete Journey đang sử dụng trong project, trước khi lọc phạm vi FMCG và thực hiện ETL.

Nguyên tắc xử lý:

* Giữ nguyên các tệp nguồn trong Raw.
* Staging lưu giá trị nguồn và thông tin truy vết lần nạp.
* Không xóa bản ghi chỉ vì có giá trị bất thường khi chưa xác định nguyên nhân.
* Phân biệt lỗi dữ liệu, nguy cơ nhân dòng khi nối bảng và giới hạn thông tin của nguồn.
* Tách điều kiện hợp lệ của từng KPI khỏi điều kiện giữ bản ghi trong kho dữ liệu.
* Ghi nhận số dòng bị loại, tổng hợp hoặc chuyển sang trạng thái cần xem xét.
* Đối soát số dòng và các số đo trước, sau từng bước xử lý.
* Các quy tắc dưới đây là đề xuất; chưa có nghĩa dữ liệu đã được làm sạch.

## 2. Kết quả kiểm tra tổng quát

### 2.1. Quy mô bảng nguồn

| Bảng                    |    Số dòng |
| ----------------------- | ---------: |
| `transactions`          |  1.469.307 |
| `promotions`            | 20.940.529 |
| `products`              |     92.331 |
| `demographics`          |        801 |
| `campaigns`             |      6.589 |
| `campaign_descriptions` |         27 |
| `coupons`               |    116.204 |
| `coupon_redemptions`    |      2.102 |

### 2.2. Kiểm tra khóa và liên kết

| Kiểm tra                                                                          | Kết quả |
| --------------------------------------------------------------------------------- | ------: |
| Dòng giao dịch trùng toàn bộ                                                      |       0 |
| Dòng giao dịch trùng `basket_id + product_id`                                     |       0 |
| Giỏ hàng liên quan nhiều hơn một hộ                                               |       0 |
| Giỏ hàng liên quan nhiều hơn một cửa hàng                                         |       0 |
| Dòng khuyến mãi trùng toàn bộ năm cột                                             |       0 |
| Dòng khuyến mãi dư so với khóa `product_id + store_id + week`                     |  12.785 |
| Dòng coupon trùng dư trên toàn bộ ba cột                                          |   4.872 |
| Dòng giao dịch có sản phẩm không khớp danh mục                                    |   4.836 |
| Mã sản phẩm giao dịch không khớp danh mục                                         |      17 |
| Dòng `coupons` có sản phẩm không khớp danh mục                                    |      16 |
| Dòng `campaigns` có chiến dịch không khớp mô tả                                   |       0 |
| Dòng `coupons` có chiến dịch không khớp mô tả                                     |       0 |
| Dòng sử dụng coupon có chiến dịch không khớp mô tả                                |       0 |
| Dòng sử dụng coupon không khớp cặp `coupon_upc + campaign_id` trong `coupons`     |       0 |
| Dòng sử dụng coupon không khớp cặp `household_id + campaign_id` trong `campaigns` |       0 |
| Dòng sử dụng coupon nằm ngoài thời gian chiến dịch tương ứng                      |       0 |

Các bảng `products`, `demographics` và `campaign_descriptions` không trùng khóa đơn tương ứng là `product_id`, `household_id` và `campaign_id`.

Bảng `campaigns` không trùng cặp `campaign_id + household_id`. Bảng `coupon_redemptions` không trùng toàn bộ bốn cột.

“Dòng trùng dư” là số dòng còn lại nếu giữ một dòng cho mỗi tổ hợp kiểm tra; không phải số nhóm bị trùng.

### 2.3. Kiểm tra giá trị

| Kiểm tra                                                         | Kết quả |
| ---------------------------------------------------------------- | ------: |
| Giá trị NULL trong `transactions`                                |       0 |
| Giá trị NULL trong `promotions`                                  |       0 |
| Giá trị âm trong `quantity`, `sales_value` và ba trường giảm giá |       0 |
| Dòng giao dịch có `quantity = 0`                                 |   8.869 |
| Dòng giao dịch có `sales_value = 0`                              |  11.226 |
| Dòng giao dịch có `coupon_disc > sales_value`                    |   3.507 |
| Sản phẩm thiếu `product_category`                                |     540 |
| Sản phẩm thiếu `product_type`                                    |     528 |
| Sản phẩm thiếu `package_size`                                    |  30.586 |
| Hộ trong `demographics` thiếu `home_ownership`                   |     233 |
| Hộ trong `demographics` thiếu `marital_status`                   |     137 |

Một dòng có thể đồng thời thuộc nhiều vấn đề. Không cộng các số lượng trên để suy ra tổng số dòng lỗi.
### 2.4. Kết quả xác minh thời gian và tuần

| Kiểm tra | Kết quả |
|---|---|
| Kiểu dữ liệu transaction_timestamp trong R | POSIXct/POSIXt |
| Thuộc tính múi giờ của timestamp | America/New_York |
| Timestamp bị thiếu | 0 |
| Week bị thiếu | 0 |
| Thời điểm giao dịch đầu tiên | 2017-01-01 06:53:26 -0500 |
| Thời điểm giao dịch cuối cùng | 2017-12-31 23:01:20 -0500 |
| Dòng giao dịch thuộc năm 2017 theo America/New_York | 1.469.307 |
| Ngày giao dịch thuộc nhiều week | 0 |
| Dòng không khớp quy tắc %W + 1 | 0 |
| Miền week trong transactions và promotions | 1–53 |
| Mã tuần chỉ xuất hiện trong một trong hai bảng | Không có |
| Ngày không có giao dịch trong năm 2017 | 25/12/2017 |

Quy tắc thời gian:

- Bảo toàn thời điểm nguồn; xác định ngày phân tích theo
  múi giờ America/New_York.
- Week giao dịch khớp quy tắc
  `as.integer(format(local_date, "%W")) + 1L`.
- Không thay week nguồn bằng tuần ISO hoặc quy tắc tuần bắt đầu Chủ nhật.
- Một số timestamp hiển thị theo UTC sang ngày 01/01/2018,
  nhưng vẫn thuộc ngày 31/12/2017 tại America/New_York.
- Việc hai bảng có cùng miền week là kiểm tra mức bao phủ mã tuần,
  không thay thế việc kiểm tra phép nối sản phẩm–cửa hàng–tuần.

Ranh giới tuần:

- Tuần 1: khoảng lịch 26/12/2016–01/01/2017;
  phần thuộc phạm vi giao dịch chỉ gồm 01/01/2017.
- Tuần 2: 02/01/2017–08/01/2017.
- Tuần 53: 25/12/2017–31/12/2017.
- Không lấy MIN/MAX ngày có giao dịch làm ranh giới tuần lịch.
- Ngày 25/12/2017 vẫn có trong Dim_Date và thuộc tuần 53.
  Không có giao dịch vào ngày này chưa đủ căn cứ kết luận
  cửa hàng đóng cửa hoặc dữ liệu bị thiếu.

Khoảng năm 2017 áp dụng cho giao dịch. Không cắt thời gian
chiến dịch ngoài năm 2017.

Các mốc thời gian trong phiên bản tệp đang sử dụng không tự động
xác nhận năm thu thập dữ liệu gốc.

## 3. Vấn đề và quy tắc xử lý dự kiến

| Mã   | Vấn đề                                                    | Phạm vi ảnh hưởng                 | Đánh giá                                    | Quy tắc dự kiến                                                                                                                               |
| ---- | --------------------------------------------------------- | --------------------------------- | ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| DQ01 | Số lượng bằng 0                                           | 8.869 dòng giao dịch              | Ảnh hưởng tính giá đơn vị                   | Giữ giá trị nguồn; gắn cờ. Giá đơn vị dẫn xuất để NULL khi số lượng bằng 0; không thay mẫu số bằng 1                                          |
| DQ02 | Giá trị bán bằng 0                                        | 11.226 dòng giao dịch             | Cần xem xét nghiệp vụ                       | Giữ bản ghi; đối chiếu số lượng và các khoản giảm giá. Không mặc định đây là lỗi hoặc hàng miễn phí                                           |
| DQ03 | Coupon nhà sản xuất lớn hơn giá trị bán                   | 3.507 dòng giao dịch              | Ảnh hưởng công thức tiền khách trả          | Giữ các trường nguồn; gắn cờ. Chưa sử dụng các dòng này cho KPI tiền khách trả dẫn xuất nếu chưa chốt quy tắc xử lý; không tự ép kết quả về 0 |
| DQ04 | Sản phẩm giao dịch không có trong danh mục                | 4.836 dòng, thuộc 17 mã           | Quan trọng đối với liên kết và phạm vi FMCG | Giữ mã nguồn; ánh xạ tới bản ghi sản phẩm chưa đủ thông tin hoặc Unknown có truy vết. Đặt phạm vi FMCG là `REVIEW`                            |
| DQ05 | Sản phẩm của coupon không có trong danh mục               | 16 dòng `coupons`                 | Quan trọng đối với liên kết                 | Giữ liên kết nguồn và gắn cờ; không tự gán sang sản phẩm khác                                                                                 |
| DQ06 | Coupon trùng toàn bộ dòng                                 | 4.872 dòng dư                     | Nguy cơ nhân liên kết                       | Giữ nguyên Raw/Staging; loại trùng theo ba cột khi xây bảng liên kết đích và ghi nhận số dòng giảm                                            |
| DQ07 | Nhiều bản ghi khuyến mãi trên cùng sản phẩm–cửa hàng–tuần | 12.785 dòng dư theo tổ hợp ba cột | Nguy cơ nhân doanh số khi nối               | Không coi là dòng trùng hoàn toàn. Tổng hợp về grain cần dùng hoặc thiết kế bảng liên kết; không tùy ý giữ dòng đầu                           |
| DQ08 | Thiếu nhóm sản phẩm                                       | 540 dòng `products`               | Ảnh hưởng phân nhóm và lọc phạm vi          | Giữ NULL ở Staging; có thể hiển thị “Chưa xác định” ở lớp phân tích. Không tự suy diễn ngành hàng                                             |
| DQ09 | Thiếu loại sản phẩm                                       | 528 dòng `products`               | Ảnh hưởng phân tích chi tiết                | Giữ NULL và gắn cờ; dùng cấp phân loại cao hơn khi có thông tin                                                                               |
| DQ10 | Thiếu quy cách đóng gói                                   | 30.586 dòng `products`            | Hạn chế so sánh giá theo đơn vị chuẩn       | Giữ NULL; không tự điền đơn vị hoặc khối lượng. Không đưa vào KPI cần quy đổi quy cách khi thiếu căn cứ                                       |
| DQ11 | Thiếu tình trạng nhà ở                                    | 233 dòng `demographics`           | Thiếu thuộc tính mô tả                      | Giữ NULL ở Staging; hiển thị nhóm chưa biết nếu sử dụng                                                                                       |
| DQ12 | Thiếu tình trạng hôn nhân                                 | 137 dòng `demographics`           | Thiếu thuộc tính mô tả                      | Giữ NULL; không suy ra từ thành phần hộ                                                                                                       |
| DQ13 | Số lượng có giá trị rất lớn                               | Giá trị lớn nhất là 89.638        | Cần xác minh đơn vị                         | Kiểm tra theo ngành hàng và sản phẩm. Không áp dụng một ngưỡng ngoại lệ chung để xóa mọi dòng                                                 |
| DQ14 | Ngày hiển thị khác nhau giữa UTC và America/New_York | Toàn bộ 1.469.307 dòng thuộc năm 2017 theo America/New_York | Cần thống nhất múi giờ phân tích | Bảo toàn thời điểm nguồn; xác định ngày giao dịch theo America/New_York trước khi tạo date_key và đối chiếu week. Không coi timestamp hiển thị sang 01/01/2018 theo UTC là giao dịch năm 2018 theo giờ địa phương |                                               |

Nếu chỉ loại 4.872 dòng trùng hoàn toàn trong `coupons`, số liên kết còn lại là **111.332 dòng**, trước các bước xử lý khác.

## 4. Rủi ro tích hợp và giới hạn của nguồn

### 4.1. Khuyến mãi có phạm vi cửa hàng khác giao dịch

Bảng `transactions` có 457 mã cửa hàng; bảng `promotions` có 112 mã cửa hàng.

Chênh lệch này cho thấy cần kiểm tra mức bao phủ khi nối. Chưa thể suy ra số dòng giao dịch được bao phủ chỉ từ số lượng cửa hàng.

Quy tắc dự kiến:

* Kiểm tra liên kết theo `product_id + store_id + week`.
* Phân biệt bản ghi khớp và không khớp thông tin khuyến mãi.
* Không tự chuyển trường hợp không khớp thành “không khuyến mãi”.
* Công bố mức bao phủ trong phân tích trưng bày và quảng cáo.

### 4.2. Nối khuyến mãi có thể nhân bản giao dịch

Bảng `promotions` không duy nhất ở grain sản phẩm–cửa hàng–tuần.

Nếu phân tích ở grain này, cần tạo một bảng tổng hợp có đúng một dòng cho mỗi tổ hợp. Các cờ trưng bày và quảng cáo phải tổng hợp từ toàn bộ bản ghi liên quan; thông tin vị trí chi tiết vẫn được giữ để truy vết.

Sau phép nối bổ sung thuộc tính, số dòng giao dịch và tổng `sales_value` phải không tăng do nhân dòng.

### 4.3. Coupon và sản phẩm có quan hệ nhiều–nhiều

Một coupon có thể áp dụng cho nhiều sản phẩm. Bảng `coupon_redemptions` không chứa `product_id` hoặc `basket_id`.

Do đó:

* Không coi mỗi dòng sau phép nối với `coupons` là một lần sử dụng coupon mới.
* Không phân bổ toàn bộ một lượt sử dụng coupon cho mọi sản phẩm đủ điều kiện.
* Không tự xác định doanh số do coupon tạo ra khi chưa có liên kết giao dịch đủ chắc chắn.

### 4.4. Nhân khẩu học không bao phủ mọi hộ

Bảng giao dịch có 2.469 hộ, còn bảng `demographics` có 801 hộ.

Việc một hộ không có hồ sơ nhân khẩu học là giới hạn của nguồn, không tự động là lỗi khóa.

Dimension hộ gia đình cần được xây từ các mã hộ liên quan trong nguồn; nhân khẩu học được bổ sung khi có. Không dùng phép nối trong với `demographics` để làm mất giao dịch của hộ chưa có thông tin.

### 4.5. Phạm vi FMCG theo quy tắc v1.3

Phạm vi triển khai sử dụng phiên bản phân loại
`1.3-cosmetics-and-exclusions`.

| Trạng thái | Số dòng giao dịch | Giá trị bán nguồn (USD) |
|---|---:|---:|
| IN_SCOPE | 1.271.042 | 3.419.948,46 |
| OUT_OF_SCOPE | 20.691 | 395.944,98 |
| REVIEW | 177.574 | 780.146,14 |
| Tổng | 1.469.307 | 4.596.039,58 |

Kết quả đối soát số dòng và tổng giá trị bán giữa ba trạng thái
với dữ liệu nguồn đều PASS.

Quy tắc áp dụng:

- Chỉ IN_SCOPE được đưa vào Fact bán hàng và KPI FMCG.
- OUT_OF_SCOPE và REVIEW vẫn được giữ trong Raw/Staging để truy vết.
- REVIEW chưa được đưa vào KPI FMCG cho đến khi có quyết định
  phân loại và phiên bản quy tắc mới.
- Sản phẩm không có thông tin danh mục được giữ mã nguồn
  và gán REVIEW; không tự coi là FMCG.
- Lưu phiên bản quy tắc cùng thông tin lần nạp.
- Khi thay đổi quy tắc, phải chạy lại phân loại, đối soát
  và cập nhật dữ liệu đích bị ảnh hưởng.
- Không cộng số giỏ hàng hoặc số hộ của ba nhóm để suy ra
  tổng số phân biệt vì một giỏ hoặc hộ có thể thuộc nhiều nhóm.

PASS xác nhận tính nhất quán của phép phân chia và tổng hợp,
không tự chứng minh mọi quyết định phân loại đều đúng về nghiệp vụ.

Chi tiết quy tắc được quản lý trong `fmcg_scope.md`.
### 4.6. Ý nghĩa giá và đơn vị cần thống nhất

Không có trường `BASE_PRICE` trực tiếp. `sales_value` không luôn là tiền khách thực trả, và số lượng giữa các nhóm sản phẩm có thể không cùng đơn vị.

Công thức giá, tiền khách trả và mức giảm giá phải được xác định trong tài liệu KPI trước khi triển khai. Không áp dụng máy móc công thức của Breakfast at the Frat.

### 4.7. Quy ước thời gian và tên cột

- Đã xác minh múi giờ America/New_York; sử dụng múi giờ này
  khi xác định ngày giao dịch và tạo date_key.
- Giữ week nguồn, đã đối chiếu khớp quy tắc %W + 1
  trên toàn bộ giao dịch; không thay bằng tuần ISO.
- Sử dụng tên múi giờ America/New_York thay vì cố định UTC-5,
  để xử lý đúng thay đổi giờ mùa hè.
- Không tự dịch thời điểm nguồn để ép ngày hiển thị;
  chỉ chuyển cách biểu diễn sang múi giờ phân tích.
- Không coi ngày trong tệp là bằng chứng duy nhất
  về năm thu thập dữ liệu gốc.
- Tệp nhân khẩu học dùng kids_count, trong khi một phần
  tài liệu nguồn ghi kid_count; triển khai theo tên cột thực tế.

## 5. Cờ chất lượng và trạng thái dự kiến

Các cờ được đặt tại bảng phù hợp, không bắt buộc đưa tất cả vào Fact bán hàng.

| Cờ hoặc trạng thái              | Ý nghĩa                                             |
| ------------------------------- | --------------------------------------------------- |
| `quantity_zero_flag`            | Số lượng nguồn bằng 0                               |
| `sales_zero_flag`               | Giá trị bán nguồn bằng 0                            |
| `coupon_exceeds_sales_flag`     | `coupon_disc > sales_value`                         |
| `product_lookup_missing_flag`   | Mã sản phẩm không khớp danh mục                     |
| `product_category_missing_flag` | Thiếu nhóm sản phẩm                                 |
| `product_type_missing_flag`     | Thiếu loại sản phẩm                                 |
| `package_size_missing_flag`     | Thiếu quy cách                                      |
| `demographics_missing_flag`     | Hộ không có hồ sơ nhân khẩu học                     |
| `promotion_match_status`        | Có hoặc không tìm thấy bản ghi khuyến mãi tương ứng |
| `fmcg_scope_status`             | `IN_SCOPE`, `OUT_OF_SCOPE` hoặc `REVIEW`            |

Thông tin audit dự kiến gồm:

* Mã lần chạy `run_id`.
* Tên bảng nguồn.
* Mã kiểm tra.
* Khóa hoặc thông tin nhận diện bản ghi.
* Số dòng ảnh hưởng.
* Hành động xử lý.
* Thời điểm kiểm tra.

Cờ chất lượng không thay thế dữ liệu nguồn và không mặc định yêu cầu loại bản ghi khỏi mọi KPI.

## 6. Đối soát và điều kiện chấp nhận khi nạp kho dữ liệu

### 6.1. Khóa và quan hệ

* Fact bán hàng không trùng grain đã chốt.
* Các Dimension không có nhiều bản ghi hiện hành cho cùng khóa nghiệp vụ, trừ khi thiết kế lịch sử cho phép.
* Mã không khớp phải được xử lý bằng bản ghi chưa biết hoặc cơ chế cách ly có truy vết.
* Bảng khuyến mãi tổng hợp phải duy nhất theo grain dùng để nối.
* Bảng liên kết coupon–sản phẩm–chiến dịch không còn dòng trùng toàn bộ sau bước loại trùng đã công bố.

### 6.2. Số dòng và số đo

* Đối soát `sales_value` và từng trường giảm giá riêng biệt.
* Đối soát số lượng theo phạm vi và đơn vị phù hợp.
* Phép nối bổ sung thuộc tính không được làm tăng số dòng hoặc doanh số ngoài thiết kế.
* Mọi dòng bị loại hoặc chuyển sang phạm vi khác phải có số lượng và lý do.
* Tổng nguồn phải đối chiếu được với các phần giữ lại, ngoài phạm vi, cần xem xét và cách ly; các phần không chồng lặp.
* Không yêu cầu số dòng của bảng khuyến mãi sau tổng hợp bằng số dòng khuyến mãi nguồn.

### 6.3. Điều kiện tính KPI

* Không chia cho 0.
* Tử số và mẫu số dùng cùng tập bản ghi hợp lệ.
* Không dùng tổng số dòng sau phép nối nhiều–nhiều để đếm giỏ hàng hoặc lượt sử dụng coupon.
* Phân biệt khuyến mãi không có và khuyến mãi chưa có thông tin.
* Không tự chuyển giá trị thiếu thành 0 khi hai trạng thái có ý nghĩa khác nhau.
* Các giá trị âm phát sinh ở lần nạp mới phải được điều tra, không tự xóa hoặc ép về 0.

### 6.4. Khả năng chạy lại

* Chạy lại cùng dữ liệu không tạo thêm bản ghi ngoài dự kiến.
* Mỗi lần chạy có trạng thái, số dòng đầu vào và đầu ra.
* Các kiểm tra không đạt phải được ghi nhận trước khi công bố dữ liệu cho dashboard.

## 7. Các kiểm tra còn cần hoàn thiện

Trước khi chốt ETL, cần bổ sung:

* Mức bao phủ khuyến mãi trên giao dịch theo sản phẩm–cửa hàng–tuần.
* Khóa sản phẩm trong `promotions` đối chiếu với `products`.
* Phân bố bản ghi khuyến mãi có nhiều vị trí trên cùng tổ hợp.
* Múi giờ timestamp và cách ánh xạ mã tuần.
* Đơn vị của các sản phẩm có số lượng lớn.
* Công thức giá và giảm giá, đặc biệt các dòng `coupon_disc > sales_value`.
* Quy mô dữ liệu sau khi áp dụng phạm vi FMCG.



## Bổ sung: Kiểm tra số lượng, doanh số và giảm giá

### 1. Phạm vi kiểm tra

- Dữ liệu giao dịch: `data/raw/complete_journey/transactions.rds`.
- Danh mục sản phẩm: `data/raw/complete_journey/products.rda`.
- Phân loại FMCG: `data/landing/fmcg_classification_v1_3/product_scope.csv`.
- Phiên bản quy tắc: `1.3-cosmetics-and-exclusions`.
- Script kiểm tra: `src/check_source_price.R`.
- Kết quả dưới đây áp dụng cho nhóm `IN_SCOPE`, gồm 1.271.042 dòng giao dịch.

### 2. Kết quả kiểm tra

| Nội dung | Kết quả |
|---|---:|
| Tổng `sales_value` | 3.419.948,46 USD |
| Tổng `retail_disc` | 710.911,57 USD |
| Tổng `coupon_disc` | 16.824,58 USD |
| Tổng `coupon_match_disc` | 4.358,46 USD |
| Giá trị thiếu, vô hạn hoặc âm trong năm trường được kiểm tra | 0 |
| `quantity` có phần thập phân | 0 |
| `quantity = 0` | 2.997 dòng |
| `quantity = 0` và `sales_value > 0` | 19 dòng |
| `quantity > 0` và `sales_value = 0` | 1.854 dòng |
| `coupon_disc > sales_value` | 402 dòng |
| `coupon_match_disc > coupon_disc` | 4 dòng |
| `coupon_match_disc > retail_disc` | 5.224 dòng |
| `coupon_match_disc > 0` và `coupon_disc = 0` | 0 dòng |
| `quantity > 100` | 1 dòng |
| `quantity` lớn nhất | 144 |

Năm trường được kiểm tra gồm `quantity`, `sales_value`, `retail_disc`,
`coupon_disc` và `coupon_match_disc`.

Các nhóm bất thường có thể giao nhau; không cộng số dòng giữa các nhóm
để suy ra tổng số dòng có vấn đề.

### 3. Quy tắc xử lý

| Trường hợp | Quy tắc |
|---|---|
| `quantity = 0` | Giữ bản ghi trong Fact; loại khỏi cả tử và mẫu của KPI giá trị bán bình quân trên đơn vị |
| `quantity = 0`, doanh số dương | Giữ doanh số khi đối soát và tính tổng; gắn cờ kiểm tra |
| `quantity > 0`, doanh số bằng 0 | Giữ bản ghi và gắn cờ; không tự kết luận là hàng tặng |
| `coupon_disc > sales_value` | Giữ dữ liệu nguồn; gắn cờ; không dùng giá trị âm suy ra làm giá khách thực trả |
| `coupon_match_disc > coupon_disc` | Gắn cờ kiểm tra; chưa coi là lỗi để xóa hoặc sửa |
| `coupon_match_disc > retail_disc` | Ghi nhận để khảo sát; không áp đặt quan hệ lớn nhỏ giữa hai loại giảm giá |
| `quantity > 100` | Gắn cờ số lượng cao; không tự xóa, cắt ngưỡng hoặc quy đổi đơn vị |
| Thiếu hoặc không rõ `package_size` | Không tự suy diễn khối lượng, thể tích hoặc số lượng trong một gói |

Dòng có `quantity = 144` thuộc sản phẩm ngô, với `package_size = '48 CT'`.
Thông tin này chưa đủ để kết luận số lượng giao dịch là số gói hoặc để
nhân/chia số lượng theo quy cách đóng gói.

### 4. Cờ chất lượng dữ liệu đề xuất

- `quantity_zero_flag`.
- `quantity_zero_sales_positive_flag`.
- `positive_quantity_zero_sales_flag`.
- `coupon_above_sales_flag`.
- `coupon_match_above_coupon_flag`.
- `high_quantity_flag`: ngưỡng khảo sát ban đầu là `quantity > 100`.

Các cờ phục vụ truy vết và phân tích độ nhạy. Chúng không đồng nghĩa
với việc bản ghi chắc chắn sai.

### 5. Giới hạn về đơn vị và công thức giá

- `quantity` được giữ theo đơn vị ghi nhận trong nguồn.
- Giá trị nguyên không chứng minh tất cả sản phẩm có cùng đơn vị đo.
- Không tự quy đổi `quantity` thành kg, lít, gói hoặc thùng từ `package_size`.
- `sales_value` không được đồng nhất với tiền khách thực trả.
- Ba trường giảm giá được lưu và tổng hợp riêng.
- Công thức `sales_value - coupon_disc` tạo ra 402 dòng âm trong `IN_SCOPE`;
  chưa dùng làm KPI tiền khách thực trả.
- Công thức `sales_value + retail_disc + coupon_match_disc` chưa được
  xác nhận là giá trị trước giảm. Việc kết quả không âm không chứng minh
  công thức đúng.
- Không xóa dòng nguồn hoặc ép giá trị suy ra về 0 để làm công thức hợp lệ.

### 6. Đối soát sau ETL

Nếu nạp toàn bộ giao dịch `IN_SCOPE` v1.3, các mốc đối soát là:

- Số dòng Fact: 1.271.042.
- Tổng `sales_value`: 3.419.948,46 USD.
- Tổng `retail_disc`: 710.911,57 USD.
- Tổng `coupon_disc`: 16.824,58 USD.
- Tổng `coupon_match_disc`: 4.358,46 USD.

Việc lọc dòng để tính KPI giá không được làm thay đổi số dòng Fact
hoặc tổng doanh số nguồn. Tiền được đối soát bằng cent hoặc kiểu
`NUMERIC`, tránh sai số số thực.