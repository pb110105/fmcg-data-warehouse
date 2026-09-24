# Câu hỏi nghiệp vụ

## 1. Mục tiêu phân tích

Hệ thống kho dữ liệu phục vụ ba nội dung chính:

* Phân tích doanh số và sản lượng.
* Phân tích giá bán và các khoản giảm giá.
* Phân tích kết quả khuyến mãi thông qua trưng bày, quảng cáo, chiến dịch và sử dụng coupon.

Các câu hỏi sử dụng dữ liệu Complete Journey và phạm vi sản phẩm FMCG được xác định trong `fmcg_scope.md`.

## 2. Câu hỏi về doanh số

| Mã     | Câu hỏi                                                                               | KPI liên quan             |
| ------ | ------------------------------------------------------------------------------------- | ------------------------- |
| BQ-S01 | Tổng giá trị bán và sản lượng trong phạm vi nghiên cứu là bao nhiêu?                  | KPI-S01, KPI-S02          |
| BQ-S02 | Giá trị bán biến động như thế nào theo ngày, tuần và tháng?                           | KPI-S01, KPI-S07          |
| BQ-S03 | Sản phẩm và ngành hàng nào đóng góp nhiều nhất vào giá trị bán?                       | KPI-S01, KPI-S06          |
| BQ-S04 | Giá trị bán khác nhau như thế nào giữa các cửa hàng trong tập dữ liệu?                | KPI-S01, KPI-S03, KPI-S05 |
| BQ-S05 | Có bao nhiêu giỏ hàng và hộ gia đình mua sản phẩm thuộc phạm vi phân tích?            | KPI-S03, KPI-S04          |
| BQ-S06 | Giá trị bán thuộc phạm vi phân tích bình quân trên một giỏ hàng thay đổi như thế nào? | KPI-S05                   |

## 3. Câu hỏi về giá và giảm giá

| Mã     | Câu hỏi                                                                                                              | KPI liên quan             |
| ------ | -------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| BQ-P01 | Giá trị bán bình quân trên một đơn vị của cùng sản phẩm thay đổi như thế nào theo thời gian và cửa hàng?             | KPI-P01                   |
| BQ-P02 | Tổng giá trị từng loại giảm giá là bao nhiêu?                                                                        | KPI-P02, KPI-P03, KPI-P04 |
| BQ-P03 | Tỷ lệ dòng mua có ghi nhận giảm giá khác nhau như thế nào giữa các sản phẩm và ngành hàng?                           | KPI-P05                   |
| BQ-P04 | Bao nhiêu phần trăm giá trị bán phát sinh trên các dòng có ghi nhận giảm giá?                                        | KPI-P06                   |
| BQ-P05 | Giá trị bán bình quân trên một đơn vị khác nhau như thế nào giữa các dòng có và không có giảm giá của cùng sản phẩm? | KPI-P01, KPI-P05          |
| BQ-P06 | Các khoản giảm giá từ nhà bán lẻ và nhà sản xuất phân bổ như thế nào theo thời gian, sản phẩm và cửa hàng?           | KPI-P02, KPI-P03, KPI-P04 |

## 4. Câu hỏi về trưng bày và quảng cáo

| Mã     | Câu hỏi                                                                                                                                                                      | KPI liên quan    |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| BQ-M01 | Bao nhiêu phần trăm giao dịch và giá trị bán có thể liên kết với thông tin trưng bày, quảng cáo?                                                                             | KPI-M01, KPI-M02 |
| BQ-M02 | Giá trị bán phân bổ như thế nào giữa các trạng thái trưng bày và quảng cáo đã xác định?                                                                                      | KPI-M03          |
| BQ-M03 | Giá trị bán bình quân trên một sản phẩm–cửa hàng–tuần có phát sinh mua khác nhau thế nào giữa các trạng thái?                                                                | KPI-M04          |
| BQ-M04 | Sản lượng bình quân trên một sản phẩm–cửa hàng–tuần có phát sinh mua khác nhau thế nào giữa các trạng thái?                                                                  | KPI-M05          |
| BQ-M05 | Trong cùng sản phẩm và cửa hàng, chênh lệch giá trị bán quan sát được giữa các tuần có hỗ trợ trưng bày/quảng cáo và các tuần không ghi nhận hai hình thức này là bao nhiêu? | KPI-M06          |
| BQ-M06 | Trạng thái kết hợp quảng cáo và trưng bày có kết quả bán hàng quan sát được khác thế nào so với từng hình thức riêng lẻ?                                                     | KPI-M04, KPI-M05 |

## 5. Câu hỏi về chiến dịch và coupon

| Mã     | Câu hỏi                                                                               | KPI liên quan    |
| ------ | ------------------------------------------------------------------------------------- | ---------------- |
| BQ-C01 | Mỗi chiến dịch được ghi nhận gửi đến bao nhiêu hộ gia đình?                           | KPI-C01          |
| BQ-C02 | Mỗi chiến dịch có bao nhiêu hộ sử dụng coupon và bao nhiêu bản ghi sử dụng?           | KPI-C02, KPI-C03 |
| BQ-C03 | Tỷ lệ hộ sử dụng ít nhất một coupon khác nhau như thế nào giữa các chiến dịch?        | KPI-C04          |
| BQ-C04 | Bình quân mỗi hộ có sử dụng coupon tạo ra bao nhiêu bản ghi sử dụng trong chiến dịch? | KPI-C05          |
| BQ-C05 | Có bao nhiêu mã coupon khác nhau được sử dụng trong từng chiến dịch?                  | KPI-C06          |

Các KPI chiến dịch–coupon được tính trên toàn bộ bản ghi chiến dịch–coupon nguồn và ghi rõ phạm vi này trên dashboard. Chưa gọi đây là kết quả sử dụng coupon riêng cho FMCG, vì bản ghi sử dụng không xác định sản phẩm thực tế đã mua.

## 6. Giới hạn diễn giải

* Giá trị bán là giá trị ghi nhận từ các hộ có trong nguồn, không phải toàn bộ doanh số của cửa hàng.
* `sales_value` phản ánh số tiền nhà bán lẻ nhận được; không đồng nhất với tiền khách hàng thực trả.
* Không phân tích theo thành phố, bang, diện tích hoặc phân khúc cửa hàng vì nguồn không cung cấp các thuộc tính đó.
* So sánh giá và sản lượng phải xét tính tương đồng của sản phẩm và đơn vị.
* Không suy ra doanh số do một chiến dịch hoặc coupon tạo ra khi thiếu liên kết giao dịch trực tiếp.
* Không coi giao dịch không khớp bảng `promotions` là không khuyến mãi.
* Không có trưng bày/quảng cáo không đồng nghĩa không có giảm giá.
* Các chênh lệch giữa nhóm chỉ là kết quả mô tả, không phải tác động nhân quả.
* Không tính lợi nhuận hoặc ROI do thiếu giá vốn và chi phí chiến dịch.

## 7. Ánh xạ đầu ra

| Nhóm câu hỏi | Nguồn chính                                                | Data Mart dự kiến         | Dashboard              |
| ------------ | ---------------------------------------------------------- | ------------------------- | ---------------------- |
| BQ-S         | `transactions`, `products`                                 | `mart_sales_overview`     | Tổng quan doanh số     |
| BQ-P         | `transactions`, `products`                                 | `mart_price_analysis`     | Giá bán và giảm giá    |
| BQ-M         | `transactions`, `promotions`, `products`                   | `mart_promotion_analysis` | Trưng bày và quảng cáo |
| BQ-C         | `campaigns`, `campaign_descriptions`, `coupon_redemptions` | `mart_campaign_coupon`    | Chiến dịch và coupon   |

Data Mart là đầu ra phục vụ phân tích, không bắt buộc tương ứng một–một với bảng Fact.
