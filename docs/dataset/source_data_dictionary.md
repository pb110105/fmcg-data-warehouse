# Data Dictionary dữ liệu nguồn

## 1. Quy ước

Tài liệu mô tả tám bảng của bộ Complete Journey đang sử dụng trong project.

* **Business key:** mã định danh nghiệp vụ trong nguồn; có thể cần kết hợp nhiều cột để xác định một dòng.
* **Measure:** số đo định lượng. Khả năng cộng hoặc tổng hợp phụ thuộc vào ý nghĩa và đơn vị.
* **Attribute:** thuộc tính mô tả.
* **Cột liên kết:** cột dùng để nối bảng; không đồng nghĩa dữ liệu nguồn đã bảo đảm ràng buộc khóa ngoại.
* **Có NULL trong nguồn:** kết quả quan sát trên các tệp đã kiểm tra, không phải quy định `NOT NULL` của cơ sở dữ liệu đích.
* **Kiểu PostgreSQL dự kiến:** đề xuất ban đầu cho dữ liệu được nạp; sẽ được xác định chính thức trong thiết kế Staging và source-to-target mapping.

Các mã định danh được giữ dưới dạng chuỗi để bảo toàn giá trị nguồn. Các trường phân loại của R được chuyển thành nhãn văn bản, không sử dụng mã số nội bộ của factor.

Quy tắc làm sạch, xử lý bản ghi bất thường và đối soát được trình bày riêng trong `data_quality_findings.md`. Công thức chỉ số dẫn xuất được trình bày trong `kpi_definitions.md`.

## 2. Bảng `transactions`

* **Tệp:** `transactions.rds`.
* **Số dòng:** 1.469.307.
* **Số cột:** 11.
* **Grain:** một sản phẩm được mua trong một giỏ hàng.
* **Khóa nghiệp vụ quan sát được:** `basket_id + product_id`; không trùng trong tệp đã kiểm tra.

| Cột nguồn               | Kiểu quan sát sau khi đọc | Kiểu PostgreSQL dự kiến | Có NULL trong nguồn | Vai trò                               | Ý nghĩa                                                                    |
| ----------------------- | ------------------------- | ----------------------- | ------------------- | ------------------------------------- | -------------------------------------------------------------------------- |
| `household_id`          | Chuỗi                     | `TEXT`                  | Không               | Cột liên kết                          | Mã hộ gia đình thực hiện giao dịch                                         |
| `store_id`              | Chuỗi                     | `TEXT`                  | Không               | Cột liên kết                          | Mã cửa hàng phát sinh giao dịch                                            |
| `basket_id`             | Chuỗi                     | `TEXT`                  | Không               | Thành phần business key               | Mã giỏ hàng hoặc lần mua                                                   |
| `product_id`            | Chuỗi                     | `TEXT`                  | Không               | Thành phần business key, cột liên kết | Mã sản phẩm được mua                                                       |
| `quantity`              | Số thực                   | `NUMERIC`               | Không               | Measure                               | Số lượng sản phẩm trong dòng giao dịch; cần xem xét đơn vị theo ngành hàng |
| `sales_value`           | Số thực                   | `NUMERIC`               | Không               | Measure                               | Giá trị bằng USD mà nhà bán lẻ nhận được từ dòng giao dịch                 |
| `retail_disc`           | Số thực                   | `NUMERIC`               | Không               | Measure                               | Khoản giảm giá do chương trình thẻ khách hàng của nhà bán lẻ               |
| `coupon_disc`           | Số thực                   | `NUMERIC`               | Không               | Measure                               | Khoản giảm giá từ coupon của nhà sản xuất                                  |
| `coupon_match_disc`     | Số thực                   | `NUMERIC`               | Không               | Measure                               | Khoản giảm giá bổ sung do nhà bán lẻ đối ứng coupon của nhà sản xuất       |
| `week`                  | Số nguyên                 | `SMALLINT`              | Không               | Cột liên kết thời gian                | Mã tuần nguồn, có giá trị từ 1 đến 53                                      |
| `transaction_timestamp` | Ngày giờ                  | `TIMESTAMP`*            | Không               | Attribute thời gian                   | Thời điểm phát sinh giao dịch                                              |

* Cần xác minh metadata múi giờ của đối tượng R trước khi chốt `TIMESTAMP` hoặc `TIMESTAMPTZ`. Không tự chuyển múi giờ hoặc tự gán múi giờ Việt Nam.

### Lưu ý về ý nghĩa

* `sales_value` không luôn bằng số tiền khách hàng thực trả vì coupon nhà sản xuất có thể được hoàn trả cho nhà bán lẻ.
* Các khoản giảm giá là giá trị của dòng giao dịch; không mặc định là mức giảm trên một đơn vị.
* Trong bản đã kiểm tra, các trường số lượng, giá trị bán và giảm giá không âm.
* Nguồn không có các cột `PRICE`, `BASE_PRICE`, `VISITS` hoặc `HHS`.
* `basket_id` cho phép đếm giỏ hàng phân biệt; `household_id` cho phép đếm hộ gia đình phân biệt.
* Một hộ gia đình không tương đương một cá nhân.
* Không mặc định mọi ngành hàng có cùng đơn vị số lượng.
* `week` phải được đối chiếu với ngày giao dịch trước khi ánh xạ lịch; không mặc định là tuần ISO.

## 3. Bảng `promotions`

* **Tệp:** `promotions.rds`.
* **Số dòng:** 20.940.529.
* **Số cột:** 5.
* **Nội dung:** vị trí trưng bày và quảng cáo theo sản phẩm, cửa hàng và tuần.
* **Đặc điểm khóa:** tổ hợp `product_id + store_id + week` không duy nhất; không có dòng trùng toàn bộ năm cột trong tệp đã kiểm tra.

| Cột nguồn          | Kiểu quan sát sau khi đọc | Kiểu PostgreSQL dự kiến | Có NULL trong nguồn | Vai trò                | Ý nghĩa                                        |
| ------------------ | ------------------------- | ----------------------- | ------------------- | ---------------------- | ---------------------------------------------- |
| `product_id`       | Chuỗi                     | `TEXT`                  | Không               | Cột liên kết           | Mã sản phẩm được ghi nhận thông tin khuyến mãi |
| `store_id`         | Chuỗi                     | `TEXT`                  | Không               | Cột liên kết           | Mã cửa hàng                                    |
| `display_location` | Phân loại                 | `TEXT`                  | Không               | Attribute              | Mã vị trí trưng bày trong cửa hàng             |
| `mailer_location`  | Phân loại                 | `TEXT`                  | Không               | Attribute              | Mã vị trí xuất hiện trong tài liệu quảng cáo   |
| `week`             | Số nguyên                 | `SMALLINT`              | Không               | Cột liên kết thời gian | Mã tuần nguồn, từ 1 đến 53                     |

### Lưu ý về ý nghĩa

* `display_location` và `mailer_location` là mã phân loại, không phải số đo.
* Mã `"0"` biểu thị không trưng bày hoặc không xuất hiện trong quảng cáo tương ứng trên bản ghi đó.
* Các mã khác phải được giải thích theo User Guide của phiên bản sử dụng.
* Không có cột `campaign_id` trong bảng này.
* Một tổ hợp sản phẩm–cửa hàng–tuần có thể có nhiều dòng vị trí khác nhau.
* Không tìm thấy bản ghi khi nối với giao dịch không đồng nghĩa chắc chắn không khuyến mãi.

## 4. Bảng `products`

* **Tệp:** `products.rda`.
* **Số dòng:** 92.331.
* **Số cột:** 7.
* **Grain:** một sản phẩm trong danh mục.
* **Business key:** `product_id`, duy nhất trong tệp đã kiểm tra.

| Cột nguồn          | Kiểu quan sát sau khi đọc | Kiểu PostgreSQL dự kiến | Có NULL trong nguồn | Vai trò      | Ý nghĩa                                            |
| ------------------ | ------------------------- | ----------------------- | ------------------- | ------------ | -------------------------------------------------- |
| `product_id`       | Chuỗi                     | `TEXT`                  | Không               | Business key | Mã sản phẩm                                        |
| `manufacturer_id`  | Mã định danh              | `TEXT`                  | Không               | Attribute    | Mã nhà sản xuất; không phải tên nhà sản xuất       |
| `department`       | Văn bản                   | `TEXT`                  | Không               | Attribute    | Nhóm ngành hàng cấp cao                            |
| `brand`            | Phân loại                 | `TEXT`                  | Không               | Attribute    | Loại nhãn hàng: nhãn riêng hoặc nhãn quốc gia      |
| `product_category` | Văn bản                   | `TEXT`                  | Có                  | Attribute    | Nhóm sản phẩm chi tiết hơn `department`            |
| `product_type`     | Văn bản                   | `TEXT`                  | Có                  | Attribute    | Loại sản phẩm chi tiết hơn `product_category`      |
| `package_size`     | Văn bản                   | `TEXT`                  | Có                  | Attribute    | Quy cách hoặc kích thước đóng gói theo mô tả nguồn |

### Lưu ý về ý nghĩa

* `brand` không cung cấp tên thương hiệu cụ thể.
* `product_id` là mã sản phẩm của bộ dữ liệu; không mặc định là mã UPC thương mại.
* `package_size` được giữ nguyên chuỗi vì có thể chứa nhiều cách biểu diễn đơn vị.
* Danh mục có cả sản phẩm ngoài FMCG; quy tắc phạm vi được trình bày trong `fmcg_scope.md`.
* Một số mã sản phẩm trong giao dịch không có bản ghi tương ứng trong danh mục; được ghi nhận trong hồ sơ chất lượng dữ liệu.

## 5. Bảng `demographics`

* **Tệp:** `demographics.rda`.
* **Số dòng:** 801.
* **Số cột:** 8.
* **Grain:** một hộ gia đình có thông tin nhân khẩu học.
* **Business key:** `household_id`, duy nhất trong tệp đã kiểm tra.

| Cột nguồn        | Kiểu quan sát sau khi đọc | Kiểu PostgreSQL dự kiến | Có NULL trong nguồn | Vai trò                    | Ý nghĩa                           |
| ---------------- | ------------------------- | ----------------------- | ------------------- | -------------------------- | --------------------------------- |
| `household_id`   | Chuỗi                     | `TEXT`                  | Không               | Business key, cột liên kết | Mã hộ gia đình                    |
| `age`            | Phân loại có thứ tự       | `TEXT`                  | Không               | Attribute                  | Nhóm tuổi được ghi nhận cho hộ    |
| `income`         | Phân loại có thứ tự       | `TEXT`                  | Không               | Attribute                  | Nhóm thu nhập của hộ              |
| `home_ownership` | Phân loại                 | `TEXT`                  | Có                  | Attribute                  | Tình trạng sở hữu hoặc thuê nhà   |
| `marital_status` | Phân loại                 | `TEXT`                  | Có                  | Attribute                  | Tình trạng hôn nhân được ghi nhận |
| `household_size` | Phân loại có thứ tự       | `TEXT`                  | Không               | Attribute                  | Nhóm quy mô hộ gia đình           |
| `household_comp` | Phân loại                 | `TEXT`                  | Không               | Attribute                  | Thành phần hộ gia đình            |
| `kids_count`     | Phân loại có thứ tự       | `TEXT`                  | Không               | Attribute                  | Nhóm số lượng trẻ em trong hộ     |

### Lưu ý về ý nghĩa

* Các nhãn khoảng tuổi, khoảng thu nhập và nhóm như `5+` không phải số chính xác.
* Không chuyển trực tiếp các nhóm này thành số để cộng hoặc tính trung bình.
* Bảng chỉ mô tả một phần hộ có giao dịch, không phải danh mục đầy đủ của mọi hộ.
* Thiếu bản ghi nhân khẩu học không có nghĩa mã hộ trong giao dịch bị lỗi.
* Tên cột thực tế là `kids_count`; một phần User Guide ghi `kid_count`. Tên cột trong tệp được ưu tiên khi triển khai.

## 6. Bảng `campaigns`

* **Tệp:** `campaigns.rda`.
* **Số dòng:** 6.589.
* **Số cột:** 2.
* **Grain:** một cặp chiến dịch–hộ gia đình.
* **Business key:** `campaign_id + household_id`, không trùng trong tệp đã kiểm tra.

| Cột nguồn      | Kiểu quan sát sau khi đọc | Kiểu PostgreSQL dự kiến | Có NULL trong nguồn | Vai trò                               | Ý nghĩa                                           |
| -------------- | ------------------------- | ----------------------- | ------------------- | ------------------------------------- | ------------------------------------------------- |
| `campaign_id`  | Chuỗi                     | `TEXT`                  | Không               | Thành phần business key, cột liên kết | Mã chiến dịch                                     |
| `household_id` | Chuỗi                     | `TEXT`                  | Không               | Thành phần business key, cột liên kết | Mã hộ được ghi nhận nhận hoặc tham gia chiến dịch |

Bảng không chứa doanh số, chi phí chiến dịch hoặc xác nhận hộ đã sử dụng coupon. Việc xuất hiện trong bảng không đồng nghĩa hộ đã mua hàng do chiến dịch.

## 7. Bảng `campaign_descriptions`

* **Tệp:** `campaign_descriptions.rda`.
* **Số dòng:** 27.
* **Số cột:** 4.
* **Grain:** một chiến dịch.
* **Business key:** `campaign_id`, duy nhất trong tệp đã kiểm tra.

| Cột nguồn       | Kiểu quan sát sau khi đọc | Kiểu PostgreSQL dự kiến | Có NULL trong nguồn | Vai trò             | Ý nghĩa                                 |
| --------------- | ------------------------- | ----------------------- | ------------------- | ------------------- | --------------------------------------- |
| `campaign_id`   | Chuỗi                     | `TEXT`                  | Không               | Business key        | Mã chiến dịch                           |
| `campaign_type` | Phân loại                 | `TEXT`                  | Không               | Attribute           | Loại chiến dịch; có ba loại trong nguồn |
| `start_date`    | Ngày                      | `DATE`                  | Không               | Attribute thời gian | Ngày bắt đầu chiến dịch                 |
| `end_date`      | Ngày                      | `DATE`                  | Không               | Attribute thời gian | Ngày kết thúc chiến dịch                |

Khoảng hoạt động chiến dịch có thể vượt ra ngoài khoảng thời gian giao dịch. Bảng không có ngân sách hoặc chi phí thực hiện chiến dịch.

## 8. Bảng `coupons`

* **Tệp:** `coupons.rda`.
* **Số dòng:** 116.204.
* **Số cột:** 3.
* **Grain nghiệp vụ:** một liên kết coupon–sản phẩm–chiến dịch.
* **Tổ hợp nhận diện liên kết:** `coupon_upc + product_id + campaign_id`.
* **Đặc điểm nguồn:** có 4.872 dòng trùng dư trên toàn bộ ba cột; tổ hợp trên chưa duy nhất trong dữ liệu thô.

| Cột nguồn     | Kiểu quan sát sau khi đọc | Kiểu PostgreSQL dự kiến | Có NULL trong nguồn | Vai trò             | Ý nghĩa                              |
| ------------- | ------------------------- | ----------------------- | ------------------- | ------------------- | ------------------------------------ |
| `coupon_upc`  | Chuỗi                     | `TEXT`                  | Không               | Thành phần liên kết | Mã coupon                            |
| `product_id`  | Chuỗi                     | `TEXT`                  | Không               | Thành phần liên kết | Mã sản phẩm mà coupon có thể áp dụng |
| `campaign_id` | Chuỗi                     | `TEXT`                  | Không               | Thành phần liên kết | Mã chiến dịch gắn với coupon         |

### Lưu ý về ý nghĩa

* `coupon_upc` không phải mã sản phẩm.
* Một coupon có thể áp dụng cho nhiều sản phẩm.
* Khi liên kết với bản ghi sử dụng coupon, cần xét cả `coupon_upc` và `campaign_id`.
* Bảng không chứa mệnh giá coupon hoặc số tiền giảm của từng lần sử dụng.
* Quy tắc xử lý dòng trùng được mô tả riêng trong hồ sơ chất lượng.

## 9. Bảng `coupon_redemptions`

* **Tệp:** `coupon_redemptions.rda`.
* **Số dòng:** 2.102.
* **Số cột:** 4.
* **Grain quan sát:** một hộ sử dụng một coupon thuộc một chiến dịch trong một ngày.
* **Tổ hợp nhận diện trong tệp:** `household_id + coupon_upc + campaign_id + redemption_date`; không trùng trong bản đã kiểm tra.

| Cột nguồn         | Kiểu quan sát sau khi đọc | Kiểu PostgreSQL dự kiến | Có NULL trong nguồn | Vai trò                               | Ý nghĩa                      |
| ----------------- | ------------------------- | ----------------------- | ------------------- | ------------------------------------- | ---------------------------- |
| `household_id`    | Chuỗi                     | `TEXT`                  | Không               | Thành phần business key, cột liên kết | Mã hộ sử dụng coupon         |
| `coupon_upc`      | Chuỗi                     | `TEXT`                  | Không               | Thành phần business key, cột liên kết | Mã coupon được sử dụng       |
| `campaign_id`     | Chuỗi                     | `TEXT`                  | Không               | Thành phần business key, cột liên kết | Mã chiến dịch của coupon     |
| `redemption_date` | Ngày                      | `DATE`                  | Không               | Thành phần business key, thời gian    | Ngày ghi nhận sử dụng coupon |

Bảng không có mã sự kiện riêng, `basket_id`, `product_id` hoặc số tiền giảm. Đếm dòng biểu thị số bản ghi sử dụng coupon được nguồn ghi nhận; không tự suy diễn thành số sản phẩm đã mua hoặc số tiền khuyến mãi.

## 10. Các quan hệ liên kết nguồn

| Bảng                 | Cột liên kết                     | Bảng liên quan          | Ý nghĩa và giới hạn                                                           |
| -------------------- | -------------------------------- | ----------------------- | ----------------------------------------------------------------------------- |
| `transactions`       | `product_id`                     | `products`              | Bổ sung thông tin sản phẩm; có mã chưa khớp danh mục                          |
| `transactions`       | `household_id`                   | `demographics`          | Bổ sung nhân khẩu học nếu có; nhiều hộ không có hồ sơ                         |
| `transactions`       | `product_id`, `store_id`, `week` | `promotions`            | Tra cứu trưng bày/quảng cáo; phía khuyến mãi có thể có nhiều dòng             |
| `campaigns`          | `campaign_id`                    | `campaign_descriptions` | Bổ sung mô tả chiến dịch                                                      |
| `campaigns`          | `household_id`                   | `demographics`          | Bổ sung thông tin hộ nếu có                                                   |
| `coupons`            | `product_id`                     | `products`              | Xác định sản phẩm áp dụng; có mã chưa khớp danh mục                           |
| `coupons`            | `campaign_id`                    | `campaign_descriptions` | Xác định chiến dịch liên quan                                                 |
| `coupon_redemptions` | `coupon_upc`, `campaign_id`      | `coupons`               | Xác định tập sản phẩm có thể áp dụng, không xác định duy nhất sản phẩm đã mua |
| `coupon_redemptions` | `household_id`, `campaign_id`    | `campaigns`             | Đối chiếu hộ và chiến dịch                                                    |
| `coupon_redemptions` | `campaign_id`                    | `campaign_descriptions` | Bổ sung loại và thời gian chiến dịch                                          |

Các quan hệ trên là quan hệ nghiệp vụ để thiết kế tích hợp. Không được mặc định tất cả là phép nối nhiều–một hoặc có thể cộng số đo sau khi nối.

## 11. Khác biệt cần lưu ý khi triển khai

* Nguồn gồm các đối tượng dữ liệu R, không có sheet Excel hoặc Glossary riêng.
* Không có bảng tra cứu cửa hàng chứa địa lý, diện tích hoặc phân khúc.
* Không có cột `campaign_id` và `coupon_upc` trong `transactions`.
* Không có cột `campaign_id` trong `promotions`.
* Không có giá cơ sở trực tiếp như `BASE_PRICE`.
* Các cột `display_location`, `mailer_location` là mã phân loại, không phải các cờ `FEATURE`, `DISPLAY`, `TPR_ONLY` của bộ cũ.
* Kiểu `NUMERIC` trong tài liệu là đề xuất giữ độ chính xác thập phân; precision và scale sẽ được chốt khi thiết kế chi tiết.
* Tên cột thực tế trong tệp là cơ sở triển khai. Khác biệt với tài liệu hướng dẫn cần được ghi nhận thay vì tự đổi tên nguồn.
