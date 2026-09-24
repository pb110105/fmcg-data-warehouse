# Dữ liệu nguồn

## 1. Bộ dữ liệu sử dụng

Project sử dụng **dunnhumby – The Complete Journey**, theo phiên bản được phân phối trong dự án R `completejourney`.

* Trang giới thiệu: https://bradleyboehmke.github.io/completejourney/
* Thư mục tải dữ liệu: https://github.com/bradleyboehmke/completejourney/tree/master/data
* Tài liệu hướng dẫn: https://bradleyboehmke.github.io/completejourney/articles/completejourney.html

## 2. Chuẩn bị dữ liệu

Tải và đặt đủ tám tệp dưới đây vào thư mục `data/raw/complete_journey/`, tính từ thư mục gốc project.

| Tệp                         | Nội dung                                         |
| --------------------------- | ------------------------------------------------ |
| `transactions.rds`          | Giao dịch mua sản phẩm                           |
| `promotions.rds`            | Thông tin trưng bày và quảng cáo                 |
| `products.rda`              | Danh mục sản phẩm                                |
| `demographics.rda`          | Thông tin nhân khẩu học của một phần hộ gia đình |
| `campaigns.rda`             | Liên kết hộ gia đình với chiến dịch              |
| `campaign_descriptions.rda` | Mô tả và thời gian chiến dịch                    |
| `coupons.rda`               | Liên kết coupon với sản phẩm và chiến dịch       |
| `coupon_redemptions.rda`    | Ghi nhận sử dụng coupon                          |

Sử dụng hai tệp đầy đủ `transactions.rds` và `promotions.rds`, không thay bằng `transactions_sample.rda` hoặc `promotions_sample.rda`.

Giữ nguyên tên và định dạng tệp. Không đổi đuôi `.rda` hoặc `.rds` thành `.csv`.

## 3. Nguyên tắc quản lý

* Giữ nguyên dữ liệu nguồn; không chỉnh sửa hoặc ghi đè trực tiếp.
* Không đưa tám tệp dữ liệu lên GitHub. Các tệp này được loại trừ bằng `.gitignore`.
* Sau khi clone repository, cần tải và đặt dữ liệu vào đúng thư mục trước khi chạy pipeline.
* Không bắt buộc chuyển nguồn sang Excel hoặc CSV.
* Nếu cần chuyển định dạng, lưu bản chuyển đổi trong `data/landing/`.
* Việc làm sạch, loại trùng và lọc phạm vi FMCG được thực hiện trong ETL.
* Kiểm kê tên tệp, kích thước và mã SHA-256 để nhận diện phiên bản dữ liệu.

## 4. Tài liệu liên quan

Các đường dẫn dưới đây tính từ thư mục gốc project:

| Tài liệu                                 | Nội dung                                     |
| ---------------------------------------- | -------------------------------------------- |
| `docs/dataset/data_source.md`            | Nguồn, phiên bản và giới hạn dữ liệu         |
| `docs/dataset/source_inventory.md`       | Kiểm kê tệp và bảng nguồn                    |
| `docs/dataset/source_data_dictionary.md` | Ý nghĩa các cột                              |
| `docs/dataset/data_quality_findings.md`  | Kết quả kiểm tra và quy tắc xử lý dự kiến    |
| `docs/dataset/fmcg_scope.md`             | Quy tắc xác định sản phẩm thuộc phạm vi FMCG |

Dữ liệu được sử dụng phục vụ học tập và nghiên cứu. Khi sử dụng hoặc phân phối lại, cần tuân thủ điều kiện của nguồn cung cấp.
