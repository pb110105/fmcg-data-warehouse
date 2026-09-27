# FMCG Retail Data Warehouse

## 1. Giới thiệu

Tiểu luận chuyên ngành với đề tài:

> **Xây dựng hệ thống kho dữ liệu bán lẻ FMCG phục vụ phân tích doanh số, giá bán và hiệu quả khuyến mãi**

Dự án sử dụng bộ dữ liệu **dunnhumby – The Complete Journey**, theo phiên bản được phân phối trong dự án R `completejourney`.

Hệ thống dự kiến tiếp nhận dữ liệu nguồn, kiểm tra chất lượng, thực hiện ETL, tổ chức kho dữ liệu đa chiều và xây dựng Data Mart phục vụ dashboard Power BI.

Đề tài được thực hiện theo hình thức cá nhân.

| MSSV     | Họ và tên          |
| -------- | ------------------ |
| 23133006 | Phạm Trần Quốc Bảo |

## 2. Mục tiêu

* Khảo sát cấu trúc và chất lượng dữ liệu.
* Xác định phạm vi sản phẩm FMCG.
* Thiết kế kho dữ liệu phục vụ nhiều nghiệp vụ liên quan.
* Xây dựng ETL có khả năng chạy lại và đối soát.
* Phân tích doanh số, giá trị bán trên đơn vị và các khoản giảm giá.
* So sánh kết quả bán hàng theo trưng bày và quảng cáo.
* Thống kê hộ nhận chiến dịch và sử dụng coupon.
* Xây dựng dashboard Power BI.

## 3. Dữ liệu nguồn

Dữ liệu được lưu tại `data/raw/complete_journey/`.

| Tệp                         |    Số dòng | Nội dung                                  |
| --------------------------- | ---------: | ----------------------------------------- |
| `transactions.rds`          |  1.469.307 | Giao dịch mua sản phẩm                    |
| `promotions.rds`            | 20.940.529 | Trưng bày và quảng cáo                    |
| `products.rda`              |     92.331 | Danh mục sản phẩm                         |
| `demographics.rda`          |        801 | Nhân khẩu học của một phần hộ gia đình    |
| `campaigns.rda`             |      6.589 | Hộ gia đình nhận chiến dịch               |
| `campaign_descriptions.rda` |         27 | Mô tả chiến dịch                          |
| `coupons.rda`               |    116.204 | Coupon áp dụng cho sản phẩm và chiến dịch |
| `coupon_redemptions.rda`    |      2.102 | Ghi nhận sử dụng coupon                   |

Các số liệu trên là quy mô nguồn trước khi lọc FMCG và xử lý chất lượng.

Bảng giao dịch có:

* 155.848 giỏ hàng phân biệt.
* 2.469 hộ gia đình.
* 457 mã cửa hàng.
* 68.509 mã sản phẩm.
* Ngày giao dịch từ 01/01/2017 đến 31/12/2017 theo múi giờ America/New_York.
* Tuần nguồn có giá trị từ 1 đến 53, khớp quy tắc `%W + 1`
  khi tính trên ngày giao dịch theo múi giờ này.

Một số timestamp khi hiển thị theo UTC thuộc ngày 01/01/2018,
nhưng vẫn thuộc ngày 31/12/2017 tại America/New_York.
Hệ thống sử dụng ngày theo America/New_York để phân tích bán hàng.

Nguồn tham khảo:

* [dunnhumby Source Files](https://www.dunnhumby.com/source-files/)
* [completejourney](https://bradleyboehmke.github.io/completejourney/)
* [User Guide](https://bradleyboehmke.github.io/completejourney/articles/completejourney.html)
* [Thư mục dữ liệu](https://github.com/bradleyboehmke/completejourney/tree/master/data)

## 4. Phạm vi

### Trong phạm vi

* Khảo sát nguồn và xây dựng Data Dictionary.
* Kiểm tra chất lượng, ánh xạ khóa và đối soát dữ liệu.
* Xác định các sản phẩm thuộc FMCG.
* Thiết kế Staging, Data Warehouse, Data Mart và audit.
* Phân tích bán hàng theo thời gian, sản phẩm và mã cửa hàng.
* Phân tích giá trị bán bình quân trên đơn vị và từng khoản giảm giá.
* So sánh bán hàng theo thông tin trưng bày, quảng cáo.
* Thống kê chiến dịch và sử dụng coupon.
* Xây dựng dashboard và đánh giá pipeline.

### Ngoài phạm vi

* Dự báo và Machine Learning.
* Khai phá giỏ hàng và RFM.
* Phân tích khách hàng cá nhân.
* Tính lợi nhuận hoặc ROI khi thiếu chi phí.
* Khẳng định tác động nhân quả của khuyến mãi.
* Phân tích địa lý cửa hàng khi chưa có dữ liệu bổ sung.
* Khái quát kết quả cho toàn bộ thị trường FMCG hoặc Việt Nam.

Bán hàng và giá được phân tích trong phạm vi FMCG đã chọn. Chỉ số chiến dịch–coupon hiện dùng toàn bộ nguồn liên quan và phải ghi rõ phạm vi, vì bản ghi sử dụng coupon không xác định sản phẩm thực tế đã mua.

## 5. Kiến trúc dự kiến

Các tệp RDA/RDS được đọc bằng Python và nạp vào PostgreSQL Staging. ETL thực hiện kiểm tra, chuẩn hóa, xác định phạm vi và ánh xạ khóa trước khi nạp Data Warehouse.

Data Mart cung cấp dữ liệu cho Power BI. Apache Airflow điều phối pipeline; schema `audit` lưu trạng thái và kết quả kiểm tra.

| Schema    | Vai trò                               |
| --------- | ------------------------------------- |
| `staging` | Dữ liệu gần nguồn và metadata lần nạp |
| `dw`      | Fact, Dimension và bảng liên kết      |
| `mart`    | Dữ liệu phục vụ các nhóm KPI          |
| `audit`   | Nhật ký, lỗi và kết quả đối soát      |

Chi tiết xem `docs/architecture/high_level_architecture.md`.

## 6. Mô hình kho dữ liệu

Mô hình gồm **3 bảng Fact, 7 bảng Dimension và 2 bảng Bridge**.
Các Fact dùng chung Dimension để phục vụ phân tích ở những mức chi tiết khác nhau.

### 6.1. Các bảng Fact

| Bảng | Một dòng biểu diễn |
|---|---|
| `fact_sales` | Một sản phẩm trong một giỏ hàng |
| `fact_promotion_weekly` | Thông tin trưng bày và quảng cáo của một sản phẩm tại một cửa hàng trong một tuần |
| `fact_coupon_redemption` | Một bản ghi sử dụng coupon theo hộ gia đình–coupon–chiến dịch–ngày |

`fact_sales` và `fact_promotion_weekly` chỉ chứa sản phẩm thuộc IN_SCOPE
theo phiên bản phân loại FMCG đã chọn.

`fact_coupon_redemption` giữ toàn bộ bản ghi sử dụng coupon nguồn.
Không tự xác định sản phẩm được mua từ danh sách sản phẩm đủ điều kiện dùng coupon.

### 6.2. Các bảng Dimension

| Bảng | Nội dung |
|---|---|
| `dim_product` | Sản phẩm, ngành hàng, quy cách và trạng thái phân loại FMCG |
| `dim_household` | Mã hộ gia đình và thông tin nhân khẩu học nếu có |
| `dim_store` | Mã cửa hàng |
| `dim_date` | Ngày và các thuộc tính lịch |
| `dim_week` | Tuần nguồn và khoảng ngày tương ứng |
| `dim_campaign` | Chiến dịch, loại chiến dịch và thời gian diễn ra |
| `dim_coupon` | Coupon được định danh bằng cặp campaign_id–coupon_upc |

### 6.3. Các bảng Bridge

| Bảng | Quan hệ |
|---|---|
| `bridge_campaign_household` | Chiến dịch–hộ gia đình nhận chiến dịch |
| `bridge_coupon_product` | Coupon–sản phẩm đủ điều kiện áp dụng |

Chiến dịch của coupon được xác định qua `dim_coupon.campaign_key`.

Không nối trực tiếp bảng Bridge vào Fact rồi cộng số đo nếu phép nối
làm nhân bản dữ liệu.

Thiết kế chi tiết được trình bày tại `docs/architecture/dimensional_model.md`.
## 7. Data Mart và dashboard

| Data Mart                 | Nội dung                                           |
| ------------------------- | -------------------------------------------------- |
| `mart_sales_overview`     | Giá trị bán, giỏ hàng, hộ mua và đóng góp doanh số |
| `mart_price_analysis`     | Giá trị bán trên đơn vị và các khoản giảm giá      |
| `mart_promotion_analysis` | Mức bao phủ và so sánh trưng bày/quảng cáo         |
| `mart_campaign_coupon`    | Hộ nhận chiến dịch và sử dụng coupon               |

Định nghĩa chi tiết nằm trong `docs/requirements/kpi_definitions.md`.

## 8. Công nghệ dự kiến

| Công nghệ        | Vai trò                                  |
| ---------------- | ---------------------------------------- |
| Python, pandas   | Đọc, khảo sát và biến đổi dữ liệu        |
| pyreadr          | Đọc các tệp RDA/RDS                      |
| PostgreSQL       | Staging, kho dữ liệu, Data Mart và audit |
| Apache Airflow   | Điều phối ETL                            |
| Docker Compose   | Quản lý các dịch vụ cục bộ               |
| Power BI Desktop | Xây dựng báo cáo và dashboard            |
| Git, GitHub      | Quản lý phiên bản và tiến độ             |

Các phiên bản thư viện và cấu hình tài nguyên sẽ được chốt khi khởi tạo môi trường.

## 9. Cấu trúc thư mục

| Đường dẫn                    | Nội dung                              |
| ---------------------------- | ------------------------------------- |
| `data/raw/complete_journey/` | Tám tệp nguồn nguyên bản              |
| `data/raw/README.md`         | Hướng dẫn chuẩn bị dữ liệu            |
| `data/landing/`              | Bản chuyển đổi trung gian nếu cần     |
| `docs/dataset/`              | Nguồn, kiểm kê, từ điển và chất lượng |
| `docs/requirements/`         | Phạm vi, câu hỏi nghiệp vụ và KPI     |
| `docs/architecture/`         | Kiến trúc hệ thống                    |
| `docs/project/`              | Kế hoạch và tiến độ                   |
| `src/`                       | Mã nguồn xử lý dữ liệu                |
| `sql/`                       | DDL, truy vấn và Data Mart            |
| `airflow/`                   | DAG và cấu hình liên quan             |
| `dashboard/`                 | Tệp Power BI và tài liệu dashboard    |

## 10. Các vấn đề cần xử lý

* Giao dịch có số lượng hoặc giá trị bán bằng 0.
* Mã sản phẩm không khớp danh mục.
* Coupon trùng dòng.
* Nhiều dòng khuyến mãi trên cùng sản phẩm–cửa hàng–tuần.
* Thiếu quy cách và một số thuộc tính sản phẩm.
* Nhân khẩu học chỉ bao phủ một phần hộ.
* Phạm vi cửa hàng của giao dịch và khuyến mãi khác nhau.
* Công thức giá cần phân biệt giá trị nhà bán lẻ nhận và tiền khách trả.

Số liệu và hướng xử lý được quản lý tập trung trong `docs/dataset/data_quality_findings.md`.

## 11. Trạng thái hiện tại

Dự án đang ở **Giai đoạn 2 – Thiết kế hệ thống**.

Đã thực hiện:

- Khảo sát tám bảng nguồn Complete Journey.
- Xây dựng hồ sơ dữ liệu, Data Dictionary và đánh giá chất lượng.
- Chốt phạm vi phân tích FMCG theo quy tắc v1.3; giữ nhóm REVIEW ngoài KPI FMCG.
- Xác minh ngày giao dịch theo múi giờ America/New_York và quy tắc tuần nguồn.
- Kiểm tra số lượng, doanh số và ba trường giảm giá; xác định các KPI được sử dụng.
- Soạn thiết kế Fact–Dimension, Staging và ánh xạ nguồn–đích.
- Viết bốn file SQL DDL tạo schema, bảng audit, Staging và kho dữ liệu.

Đang thực hiện:

- Rà soát tính nhất quán giữa README, kiến trúc, mapping, KPI và DDL.
- Chuẩn bị kiểm thử DDL trên PostgreSQL.

Chưa thực hiện:

- Triển khai môi trường Docker Compose và cơ sở dữ liệu.
- Xây dựng ETL nạp Staging, Dimension và Fact.
- Triển khai Airflow, Data Mart và dashboard Power BI.

DDL hiện đã được soạn nhưng chưa xác nhận chạy thành công trên PostgreSQL.
Các công thức giá trước giảm, tiền khách thực trả và tỷ lệ giảm giá kết hợp
chưa được xác minh nên chưa đưa vào KPI chính thức.

## 12. Hướng dẫn sử dụng hiện tại

1. Chuẩn bị đủ tám tệp tại `data/raw/complete_journey/`.
2. Đọc hồ sơ nguồn và kiểm kê trong `docs/dataset/`.
3. Đọc câu hỏi nghiệp vụ và định nghĩa KPI.
4. Theo dõi các việc còn lại trong `docs/project/roadmap.md`.

Dự án chưa có phiên bản chạy hoàn chỉnh. Lệnh cài đặt, khởi tạo cơ sở dữ liệu và chạy pipeline sẽ được bổ sung sau khi triển khai.

Không đưa dữ liệu nguồn, mật khẩu, `.env` hoặc dữ liệu vận hành lên GitHub.
Các mốc thời gian là giá trị trong phiên bản tệp đang sử dụng,
không tự động xác nhận năm thu thập dữ liệu gốc.