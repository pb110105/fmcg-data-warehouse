# Nguồn dữ liệu

## 1. Thông tin chung

* **Tên bộ dữ liệu:** The Complete Journey.
* **Đơn vị cung cấp dữ liệu gốc:** dunnhumby.
* **Phiên bản sử dụng:** bộ dữ liệu được phân phối trong dự án R `completejourney` của Brad Boehmke.
* **Trang nguồn dunnhumby:** https://www.dunnhumby.com/source-files/
* **Trang giới thiệu phiên bản sử dụng:** https://bradleyboehmke.github.io/completejourney/
* **Kho phân phối dữ liệu:** https://github.com/bradleyboehmke/completejourney/tree/master/data
* **Tài liệu hướng dẫn:** https://bradleyboehmke.github.io/completejourney/articles/completejourney.html
* **Ngày kiểm tra tài liệu trực tuyến:** 22/09/2026.
* **Định dạng dữ liệu:** sáu tệp `.rda` và hai tệp `.rds`.
* **Mục đích sử dụng:** học tập và thực hiện tiểu luận chuyên ngành.

Đề tài sử dụng dữ liệu giao dịch bán lẻ, sản phẩm, hộ gia đình, chiến dịch và coupon. Các thông tin này phục vụ xây dựng kho dữ liệu và phân tích doanh số, giá bán, mức giảm giá cùng kết quả khuyến mãi quan sát được.

Các số liệu trong tài liệu này được xác định từ tám tệp sử dụng trong project. Không sử dụng lẫn số liệu quy mô của các phiên bản Complete Journey khác.

## 2. Phạm vi dữ liệu

### 2.1. Danh sách tệp nguồn

| Tệp                         |    Số dòng | Số cột | Nội dung                                                         |
| --------------------------- | ---------: | -----: | ---------------------------------------------------------------- |
| `transactions.rds`          |  1.469.307 |     11 | Giao dịch mua sản phẩm                                           |
| `promotions.rds`            | 20.940.529 |      5 | Thông tin trưng bày và quảng cáo theo sản phẩm, cửa hàng và tuần |
| `products.rda`              |     92.331 |      7 | Danh mục sản phẩm                                                |
| `demographics.rda`          |        801 |      8 | Thông tin nhân khẩu học của một phần hộ gia đình                 |
| `campaigns.rda`             |      6.589 |      2 | Liên kết hộ gia đình với chiến dịch                              |
| `campaign_descriptions.rda` |         27 |      4 | Loại và thời gian chiến dịch                                     |
| `coupons.rda`               |    116.204 |      3 | Liên kết coupon với sản phẩm và chiến dịch                       |
| `coupon_redemptions.rda`    |      2.102 |      4 | Ghi nhận sử dụng coupon                                          |

Hai tệp `transactions.rds` và `promotions.rds` là bản đầy đủ của phiên bản đang sử dụng, không phải các bảng mẫu `transactions_sample` và `promotions_sample`.

Số dòng trên phản ánh dữ liệu nguồn trước khi loại trùng, xử lý chất lượng hoặc lọc phạm vi FMCG.

### 2.2. Quy mô giao dịch

| Thuộc tính                  |   Giá trị |
| --------------------------- | --------: |
| Số dòng giao dịch           | 1.469.307 |
| Số giỏ hàng phân biệt       |   155.848 |
| Số hộ gia đình có giao dịch |     2.469 |
| Số mã cửa hàng có giao dịch |       457 |
| Số mã sản phẩm có giao dịch |    68.509 |
| Số sản phẩm trong danh mục  |    92.331 |
| Số mã tuần trong giao dịch  |        53 |

Số sản phẩm có giao dịch được đếm trực tiếp từ bảng `transactions`, bao gồm cả các mã chưa tìm thấy thông tin tương ứng trong bảng `products`.

### 2.3. Phạm vi thời gian

Theo giá trị đọc được từ các tệp:

* Giao dịch có `transaction_timestamp` từ ngày **01/01/2017 đến ngày 01/01/2018**; có 534 dòng thuộc đầu ngày 01/01/2018.
* Bản ghi sử dụng coupon có ngày từ **01/01/2017 đến 31/12/2017**.
* Ngày bắt đầu chiến dịch sớm nhất là **14/11/2016**; ngày kết thúc chiến dịch muộn nhất là **28/02/2018**.
* Bảng khuyến mãi sử dụng mã `week` từ 1 đến 53.

Đây là các mốc thời gian trong phiên bản dữ liệu đang sử dụng, chưa đủ để xác nhận thời điểm thu thập dữ liệu gốc. Ngày cập nhật tài liệu hoặc kho mã nguồn không được xem là năm phát sinh giao dịch.

Việc ánh xạ mã tuần nguồn sang lịch ngày phải được kiểm tra trong giai đoạn thiết kế; không mặc định mã tuần nguồn là tuần ISO.

### 2.4. Mức độ chi tiết

Một dòng trong bảng `transactions` thể hiện một sản phẩm được mua trong một giỏ hàng, gắn với hộ gia đình, cửa hàng và thời điểm giao dịch.

Trong dữ liệu đã kiểm tra, tổ hợp `basket_id + product_id` không trùng. Đây là cơ sở xác định grain dự kiến của Fact bán hàng.

Bảng `promotions` mô tả vị trí trưng bày và quảng cáo theo sản phẩm–cửa hàng–tuần. Một tổ hợp này có thể xuất hiện nhiều dòng với thông tin vị trí khác nhau, vì vậy không được mặc định tổ hợp ba cột là khóa duy nhất của bảng nguồn.

### 2.5. Phạm vi sản phẩm

Danh mục nguồn gồm nhiều ngành hàng và có cả sản phẩm, dịch vụ ngoài phạm vi FMCG.

Đề tài sẽ xác định tập sản phẩm sử dụng dựa trên `department`, `product_category` và `product_type`. Quy tắc giữ, loại và các trường hợp cần xem xét được ghi riêng trong `fmcg_scope.md`.

Các số liệu quy mô trong tài liệu này là quy mô toàn bộ nguồn. Quy mô sau khi lọc FMCG sẽ được thống kê riêng.

## 3. Nguyên tắc quản lý dữ liệu nguồn

* Lưu nguyên tám tệp trong `data/raw/complete_journey/`.
* Không chỉnh sửa hoặc ghi đè lên các tệp nguồn.
* Không đưa tệp dữ liệu nguồn lên GitHub; sử dụng `.gitignore` để loại trừ.
* Giữ hướng dẫn nguồn và cách chuẩn bị dữ liệu trong `data/raw/README.md`.
* Nếu cần chuyển đổi định dạng để phục vụ nạp dữ liệu, lưu bản chuyển đổi ở `data/landing/`; bản nguồn vẫn được giữ nguyên.
* Không bắt buộc chuyển toàn bộ dữ liệu sang CSV hoặc Excel.
* Việc làm sạch, lọc phạm vi và ánh xạ khóa được thực hiện trong pipeline ETL.
* Ghi nhận tên tệp, kích thước, mã kiểm tra SHA-256 và thời điểm tiếp nhận khi lập hồ sơ kiểm kê.
* Ghi nhận số dòng trước và sau các bước xử lý để phục vụ đối soát.
* Sử dụng tài liệu hướng dẫn của đúng phiên bản `completejourney` để giải thích các trường dữ liệu.

## 4. Giới hạn dữ liệu và phân tích

### 4.1. Phạm vi đại diện

Dữ liệu phản ánh hoạt động mua của các hộ gia đình được ghi nhận trong bộ dữ liệu. Tổng doanh số tính được không được mặc định là toàn bộ doanh số của các cửa hàng.

Kết quả không đại diện cho toàn bộ thị trường FMCG hoặc thị trường bán lẻ Việt Nam.

### 4.2. Thông tin cửa hàng và hộ gia đình

* Các tệp sử dụng không cung cấp bảng thông tin địa lý hoặc đặc điểm cửa hàng.
* Có thể phân tích theo mã cửa hàng, nhưng chưa có cơ sở phân tích theo thành phố, bang, diện tích hoặc phân khúc cửa hàng.
* Thông tin nhân khẩu học chỉ có cho 801 hộ; thiếu thông tin nhân khẩu học không đồng nghĩa giao dịch của hộ đó không hợp lệ.
* `household_id` đại diện cho hộ gia đình, không phải một cá nhân cụ thể.

### 4.3. Giá bán và giảm giá

* Không có cột `BASE_PRICE` trực tiếp như bộ Breakfast at the Frat.
* `sales_value` biểu diễn giá trị nhà bán lẻ nhận được, không luôn bằng số tiền khách hàng thực trả khi có coupon nhà sản xuất.
* Công thức giá đơn vị và giảm giá phải được định nghĩa riêng trong tài liệu KPI, có điều kiện xử lý số lượng bằng 0.
* Không mặc định số lượng của mọi ngành hàng có cùng đơn vị để cộng hoặc so sánh giá trực tiếp.
* Không có đầy đủ giá vốn và chi phí chiến dịch để tính lợi nhuận hoặc ROI khuyến mãi.

### 4.4. Liên kết khuyến mãi và coupon

* Bảng khuyến mãi có 112 mã cửa hàng, trong khi giao dịch có 457 mã cửa hàng.
* Giao dịch không nối được với thông tin khuyến mãi không được tự động xem là không khuyến mãi.
* Một coupon có thể áp dụng cho nhiều sản phẩm; cần kiểm soát quan hệ nhiều–nhiều khi tích hợp.
* Bảng sử dụng coupon không có `basket_id` hoặc `product_id`, nên không thể luôn xác định chính xác dòng giao dịch đã sử dụng coupon.
* Không tự gán mọi giao dịch của một hộ trong thời gian chiến dịch là doanh số do chiến dịch tạo ra.

### 4.5. Chất lượng và diễn giải

Dữ liệu có các vấn đề về giá trị thiếu, trùng dòng, số lượng bằng 0 và liên kết sản phẩm không khớp. Chi tiết kiểm tra và hướng xử lý được trình bày trong `data_quality_findings.md`.

Phân tích khuyến mãi được thực hiện theo hướng mô tả và so sánh. Chênh lệch doanh số hoặc sản lượng giữa các nhóm không được diễn giải thành quan hệ nhân quả.

## 5. Tài liệu nguồn

1. dunnhumby, *Source Files*.
   https://www.dunnhumby.com/source-files/

2. Brad Boehmke, *completejourney*.
   https://bradleyboehmke.github.io/completejourney/

3. Brad Boehmke, *The Complete Journey User Guide*.
   https://bradleyboehmke.github.io/completejourney/articles/completejourney.html
   Kiểm tra ngày 22/09/2026.

4. Brad Boehmke, *completejourney — Data directory*.
   https://github.com/bradleyboehmke/completejourney/tree/master/data

5. Tám tệp RDA/RDS lưu tại `data/raw/complete_journey/`: cơ sở kiểm kê quy mô và kiểm tra chất lượng dữ liệu của project.
