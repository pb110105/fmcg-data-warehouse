# Kiểm kê dữ liệu nguồn

## 1. Phạm vi kiểm kê

Project sử dụng bộ **The Complete Journey**, theo phiên bản được phân phối trong dự án R `completejourney`.

Vị trí lưu nguồn:

`data/raw/complete_journey/`

Bộ nguồn gồm sáu tệp `.rda` và hai tệp `.rds`. Hai bảng giao dịch và khuyến mãi sử dụng bản đầy đủ, không sử dụng bảng mẫu.

Các số liệu trong tài liệu được kiểm kê từ bộ tệp đã cung cấp cho project. Đây chưa phải quy mô dữ liệu sau xử lý hoặc sau khi lọc sản phẩm FMCG.

## 2. Danh sách tệp

| Tệp                         | Định dạng | Kích thước (byte) | Bảng dữ liệu            |
| --------------------------- | --------- | ----------------: | ----------------------- |
| `transactions.rds`          | RDS       |        12.775.661 | `transactions`          |
| `promotions.rds`            | RDS       |        24.976.951 | `promotions`            |
| `products.rda`              | RDA       |           869.019 | `products`              |
| `demographics.rda`          | RDA       |             4.237 | `demographics`          |
| `campaigns.rda`             | RDA       |             8.264 | `campaigns`             |
| `campaign_descriptions.rda` | RDA       |               496 | `campaign_descriptions` |
| `coupons.rda`               | RDA       |           324.969 | `coupons`               |
| `coupon_redemptions.rda`    | RDA       |             8.370 | `coupon_redemptions`    |

Kích thước là dung lượng tệp, không phải bộ nhớ cần thiết khi đọc dữ liệu.

Mã SHA-256 và thời điểm tiếp nhận từng tệp cần được bổ sung khi lập manifest nguồn. Không sử dụng riêng tên hoặc kích thước tệp để khẳng định hai phiên bản có nội dung giống nhau.

## 3. Kiểm kê bảng và mức độ chi tiết

| Bảng                    |    Số dòng | Số cột | Grain hoặc nội dung một dòng                                                 | Khóa và đặc điểm                                           |
| ----------------------- | ---------: | -----: | ---------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `transactions`          |  1.469.307 |     11 | Một sản phẩm được mua trong một giỏ hàng                                     | `basket_id + product_id` không trùng trong bản đã kiểm tra |
| `promotions`            | 20.940.529 |      5 | Thông tin vị trí trưng bày và quảng cáo của sản phẩm tại cửa hàng trong tuần | `product_id + store_id + week` không duy nhất              |
| `products`              |     92.331 |      7 | Một sản phẩm trong danh mục                                                  | `product_id` duy nhất                                      |
| `demographics`          |        801 |      8 | Một hộ có thông tin nhân khẩu học                                            | `household_id` duy nhất                                    |
| `campaigns`             |      6.589 |      2 | Một hộ được ghi nhận nhận chiến dịch                                         | `campaign_id + household_id` duy nhất                      |
| `campaign_descriptions` |         27 |      4 | Một chiến dịch                                                               | `campaign_id` duy nhất                                     |
| `coupons`               |    116.204 |      3 | Một liên kết coupon–sản phẩm–chiến dịch                                      | Có dòng trùng toàn bộ ba cột                               |
| `coupon_redemptions`    |      2.102 |      4 | Một bản ghi hộ sử dụng coupon thuộc chiến dịch trong một ngày                | Toàn bộ bốn cột không trùng trong bản đã kiểm tra          |

Các khóa quan sát được cần được kiểm tra lại khi thay phiên bản nguồn. Chúng chưa đồng nghĩa với ràng buộc đã được triển khai trong cơ sở dữ liệu.

## 4. Quy mô giao dịch

| Thuộc tính                          |   Giá trị |
| ----------------------------------- | --------: |
| Số dòng giao dịch                   | 1.469.307 |
| Số giỏ hàng phân biệt               |   155.848 |
| Số hộ gia đình có giao dịch         |     2.469 |
| Số mã cửa hàng có giao dịch         |       457 |
| Số mã sản phẩm có giao dịch         |    68.509 |
| Số mã tuần                          |        53 |
| Dòng trùng toàn bộ                  |         0 |
| Dòng trùng `basket_id + product_id` |         0 |

Một giỏ hàng không liên quan nhiều hơn một hộ hoặc một cửa hàng trong bản đã kiểm tra.

Số mã sản phẩm có giao dịch được đếm trực tiếp từ `transactions`, bao gồm cả mã không khớp danh mục `products`.

Tổng giá trị bán và các khoản giảm giá sẽ được ghi nhận làm số kiểm soát khi thiết kế đối soát ETL. Tổng số lượng cần được diễn giải theo đơn vị phù hợp với từng nhóm sản phẩm.

## 5. Phạm vi thời gian

| Bảng                    | Trường thời gian        | Phạm vi quan sát                                                       |
| ----------------------- | ----------------------- | ---------------------------------------------------------------------- |
| `transactions`          | `transaction_timestamp` | 01/01/2017 11:53:26 đến 01/01/2018 04:01:20, theo kết quả đọc hiện tại |
| `transactions`          | `week`                  | 1–53                                                                   |
| `promotions`            | `week`                  | 1–53                                                                   |
| `campaign_descriptions` | `start_date`            | 14/11/2016 đến 28/12/2017                                              |
| `campaign_descriptions` | `end_date`              | 16/01/2017 đến 28/02/2018                                              |
| `coupon_redemptions`    | `redemption_date`       | 01/01/2017 đến 31/12/2017                                              |

Lưu ý:

* Có 534 dòng giao dịch mang timestamp thuộc đầu ngày 01/01/2018 theo cách đọc hiện tại.
* Cần xác minh metadata múi giờ trước khi chốt ngày giao dịch dùng trong kho dữ liệu.
* Mã tuần nguồn chưa được mặc định là tuần ISO.
* Thời gian chiến dịch có thể vượt ngoài khoảng quan sát giao dịch và sử dụng coupon.
* Các ngày trong tệp không tự động chứng minh năm thu thập dữ liệu gốc.

## 6. Danh mục sản phẩm

| Thuộc tính         | Số giá trị phân biệt, không tính NULL |
| ------------------ | ------------------------------------: |
| `product_id`       |                                92.331 |
| `manufacturer_id`  |                                 6.471 |
| `department`       |                                    32 |
| `brand`            |                                     2 |
| `product_category` |                                   303 |
| `product_type`     |                                 2.378 |

`brand` biểu thị loại nhãn hàng, không phải tên thương hiệu cụ thể.

Một số nhóm có nhiều sản phẩm:

| `department` | Số sản phẩm |
| ------------ | ----------: |
| `GROCERY`    |      39.023 |
| `DRUG GM`    |      31.540 |
| `PRODUCE`    |       3.117 |
| `COSMETICS`  |       3.011 |
| `NUTRITION`  |       2.914 |
| `MEAT`       |       2.542 |
| `MEAT-PCKGD` |       2.427 |
| `DELI`       |       2.359 |
| `PASTRY`     |       2.149 |

Bảng trên chỉ liệt kê một số nhóm lớn, không phải toàn bộ 32 nhóm và không phải danh sách FMCG đã được chọn.

Danh mục còn có nhiên liệu, dịch vụ và hàng hóa ngoài phạm vi. Quy tắc lựa chọn được quản lý trong `fmcg_scope.md`.

## 7. Hộ gia đình, chiến dịch và coupon

| Nội dung                                 | Số lượng |
| ---------------------------------------- | -------: |
| Hộ có thông tin trong `demographics`     |      801 |
| Hộ xuất hiện trong `campaigns`           |    1.559 |
| Chiến dịch trong `campaign_descriptions` |       27 |
| Loại chiến dịch                          |        3 |
| Liên kết hộ–chiến dịch                   |    6.589 |
| Mã coupon phân biệt trong `coupons`      |      981 |
| Mã sản phẩm trong `coupons`              |   41.857 |
| Hộ có bản ghi sử dụng coupon             |      410 |
| Mã coupon được sử dụng                   |      491 |
| Chiến dịch có bản ghi sử dụng coupon     |       26 |
| Bản ghi sử dụng coupon                   |    2.102 |

Các số lượng hộ ở từng bảng có phạm vi khác nhau; không cộng lại để tính tổng số hộ.

Một mã coupon có thể liên quan nhiều sản phẩm hoặc chiến dịch. Số mã coupon phân biệt không tương đương số liên kết coupon–chiến dịch hoặc số coupon được phát hành.

## 8. Thông tin trưng bày và quảng cáo

| Thuộc tính                                         |    Giá trị |
| -------------------------------------------------- | ---------: |
| Số dòng `promotions`                               | 20.940.529 |
| Mã sản phẩm phân biệt                              |     59.800 |
| Mã cửa hàng phân biệt                              |        112 |
| Mã tuần phân biệt                                  |         53 |
| Mã `display_location` phân biệt                    |         10 |
| Mã `mailer_location` phân biệt                     |         11 |
| Dòng trùng toàn bộ năm cột                         |          0 |
| Dòng dư theo tổ hợp `product_id + store_id + week` |     12.785 |

“Dòng dư theo tổ hợp” là số dòng còn lại nếu giữ một dòng cho mỗi tổ hợp ba cột, không phải số nhóm bị lặp.

Các dòng này có thể khác vị trí trưng bày hoặc quảng cáo. Không được xóa tùy ý như dòng trùng hoàn toàn.

Phạm vi 112 cửa hàng của bảng khuyến mãi khác với 457 cửa hàng trong giao dịch. Mức bao phủ thực tế trên giao dịch cần được tính bằng phép đối chiếu khóa.

## 9. Quan hệ giữa các bảng

| Bảng con hoặc nghiệp vụ | Cột đối chiếu                    | Bảng liên quan                    | Kết quả hoặc lưu ý                                   |
| ----------------------- | -------------------------------- | --------------------------------- | ---------------------------------------------------- |
| `transactions`          | `product_id`                     | `products`                        | 4.836 dòng thuộc 17 mã chưa khớp                     |
| `transactions`          | `household_id`                   | `demographics`                    | Nhân khẩu học chỉ có cho một phần hộ                 |
| `transactions`          | `product_id`, `store_id`, `week` | `promotions`                      | Cần tổng hợp hoặc kiểm soát nhiều dòng trước khi nối |
| `campaigns`             | `campaign_id`                    | `campaign_descriptions`           | Không có dòng không khớp                             |
| `coupons`               | `campaign_id`                    | `campaign_descriptions`           | Không có dòng không khớp                             |
| `coupons`               | `product_id`                     | `products`                        | Có 16 dòng chưa khớp                                 |
| `coupon_redemptions`    | `coupon_upc`, `campaign_id`      | Các cặp phân biệt trong `coupons` | Không có bản ghi không khớp                          |
| `coupon_redemptions`    | `household_id`, `campaign_id`    | `campaigns`                       | Không có bản ghi không khớp                          |
| `coupon_redemptions`    | `campaign_id`                    | `campaign_descriptions`           | Không có bản ghi không khớp                          |

Không có bảng tra cứu cửa hàng riêng trong tám tệp nguồn.

Bảng `transactions` không có `campaign_id` hoặc `coupon_upc`. Bảng `coupon_redemptions` không có `basket_id` hoặc `product_id`. Vì vậy, không có khóa trực tiếp xác định chính xác giao dịch mua hàng của từng lần sử dụng coupon.

## 10. Phân biệt kiểm kê và xử lý dữ liệu

Tài liệu này ghi nhận cấu trúc và quy mô nguồn, không quy định toàn bộ cách làm sạch.

Các nội dung liên quan được quản lý tại:

| Tài liệu                             | Vai trò                                  |
| ------------------------------------ | ---------------------------------------- |
| `data_source.md`                     | Xuất xứ, phiên bản và giới hạn sử dụng   |
| `source_data_dictionary.md`          | Ý nghĩa và kiểu dữ liệu của từng cột     |
| `data_quality_findings.md`           | Vấn đề chất lượng và hướng xử lý dự kiến |
| `fmcg_scope.md`                      | Phạm vi sản phẩm được chọn               |
| `../requirements/kpi_definitions.md` | Công thức và điều kiện tính KPI          |

Sau khi chốt phạm vi FMCG và chạy ETL, cần bổ sung bảng đối soát riêng cho số dòng nguồn, số dòng ngoài phạm vi, số dòng cần xem xét và số dòng được sử dụng. Không thay thế số liệu nguồn trong tài liệu này bằng số liệu sau xử lý.
