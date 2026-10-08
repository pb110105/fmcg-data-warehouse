# FMCG Retail Data Warehouse

## 1. Giới thiệu

Tiểu luận chuyên ngành với đề tài:

> **Xây dựng hệ thống kho dữ liệu bán lẻ FMCG phục vụ phân tích doanh số, giá bán và hiệu quả khuyến mãi**

Dự án sử dụng bộ dữ liệu **dunnhumby – The Complete Journey**, theo phiên bản được phân phối trong dự án R `completejourney`.

Hệ thống đã tiếp nhận dữ liệu nguồn, kiểm tra chất lượng và thực hiện ETL vào kho dữ liệu PostgreSQL. Các bước tiếp theo gồm điều phối bằng Airflow, xây dựng Data Mart và dashboard Power BI.

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

## 5. Kiến trúc hệ thống

Các tệp RDA/RDS được đọc bằng Python và nạp vào PostgreSQL Staging. ETL thực hiện kiểm tra, chuẩn hóa, xác định phạm vi và ánh xạ khóa trước khi nạp Data Warehouse.

Đã triển khai luồng Raw → Staging → Data Warehouse;
schema `audit` lưu trạng thái và kết quả kiểm tra.

Apache Airflow, Data Mart và Power BI là các thành phần sẽ triển khai
ở giai đoạn tiếp theo. Schema `mart` đã được tạo nhưng chưa có
các bảng hoặc view phục vụ phân tích.

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
Các Data Mart dưới đây thuộc thiết kế dự kiến, chưa được triển khai.
| Data Mart                 | Nội dung                                           |
| ------------------------- | -------------------------------------------------- |
| `mart_sales_overview`     | Giá trị bán, giỏ hàng, hộ mua và đóng góp doanh số |
| `mart_price_analysis`     | Giá trị bán trên đơn vị và các khoản giảm giá      |
| `mart_promotion_analysis` | Mức bao phủ và so sánh trưng bày/quảng cáo         |
| `mart_campaign_coupon`    | Hộ nhận chiến dịch và sử dụng coupon               |
Các Data Mart dưới đây thuộc thiết kế dự kiến, chưa được triển khai.
Dashboard Power BI sẽ được xây dựng sau khi hoàn thiện Data Mart.
Định nghĩa chi tiết nằm trong `docs/requirements/kpi_definitions.md`.

## 8. Công nghệ sử dụng và kế hoạch triển khai

| Công nghệ        | Vai trò                                  |
| ---------------- | ---------------------------------------- |
| Python, pandas   | Đọc, khảo sát và biến đổi dữ liệu        |
| pyreadr          | Đọc các tệp RDA/RDS                      |
| PostgreSQL       | Staging, kho dữ liệu, Data Mart và audit |
| Apache Airflow   | Điều phối ETL                            |
| Docker Compose   | Quản lý các dịch vụ cục bộ               |
| Power BI Desktop | Xây dựng báo cáo và dashboard            |
| Git, GitHub      | Quản lý phiên bản và tiến độ             |

Môi trường Python sử dụng `.venv`. Các thư viện được khai báo trong
`requirements.txt`; phiên bản môi trường đã cài được ghi trong
`requirements-lock.txt`. PostgreSQL được triển khai bằng Docker Compose.
Airflow và Power BI thuộc các giai đoạn tiếp theo.

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

## 10. Chất lượng dữ liệu và giới hạn

Các vấn đề dưới đây đã được nhận diện. ETL đã áp dụng quy tắc
loại trùng, tổng hợp, giữ giá trị thiếu hoặc gắn cờ phù hợp;
các giới hạn của nguồn vẫn cần được xét khi phân tích.

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

Đã hoàn thành **Giai đoạn 4 – Xây dựng ETL và nạp kho dữ liệu**.
Chuẩn bị chuyển sang Giai đoạn 5 – Điều phối bằng Apache Airflow.

Các kết quả đã thực hiện:

- Khảo sát tám bảng nguồn Complete Journey.
- Phân loại FMCG theo quy tắc `1.3-cosmetics-and-exclusions`.
- Xác minh ngày giao dịch theo `America/New_York` và tuần nguồn.
- Hoàn thiện thiết kế, mapping và triển khai DDL trên PostgreSQL.
- Thiết lập môi trường Python và PostgreSQL bằng Docker Compose.
- Nạp đủ tám bảng Staging; đối soát số dòng và kiểm tra chạy lại.
- Nạp đủ 7 Dimension, 2 Bridge và 3 Fact.
- Đối soát DW: 89 kiểm tra PASS, không có kiểm tra thất bại.
- Kiểm tra chạy lại không nhân bản và giữ nguyên khóa Dimension.
- Kiểm thử rollback và thử lại sau lỗi chương trình giả lập.
- Chốt `dw_load_id=2`, nguồn `etl_batch_id=1`, trạng thái `SUCCESS`.

### Quy mô các bảng Fact

| Bảng | Số dòng | Phạm vi |
|---|---:|---|
| `fact_sales` | 1.271.042 | Sản phẩm IN_SCOPE |
| `fact_promotion_weekly` | 17.485.242 | Sản phẩm IN_SCOPE, tổng hợp theo sản phẩm–cửa hàng–tuần |
| `fact_coupon_redemption` | 2.102 | Toàn bộ nguồn sử dụng coupon |

Tổng `sales_value` trong Fact Sales là 3.419.948,46 USD.

Có 971.514 dòng bán hàng không khớp bản ghi khuyến mãi theo
sản phẩm–cửa hàng–tuần. Các dòng này phải được giữ ở nhóm
“Không có thông tin khuyến mãi khớp”, không tự coi là không khuyến mãi.

Kiểm thử phục hồi hiện bao gồm lỗi chương trình giả lập trước commit,
rollback và thử lại; chưa kiểm thử tắt Docker đột ngột hoặc mất điện.

Chưa triển khai:

- DAG Airflow điều phối pipeline.
- Data Mart và dashboard Power BI.
- Đánh giá, báo cáo và trình bày cuối kỳ.

Nhóm REVIEW tiếp tục nằm ngoài KPI FMCG.
Các công thức giá trước giảm, tiền khách thực trả và tỷ lệ giảm giá
kết hợp chưa xác minh tiếp tục nằm ngoài KPI chính thức.

## 12. Hướng dẫn sử dụng hiện tại

Thực hiện các lệnh tại thư mục gốc project bằng Windows CMD.
Môi trường đã kiểm tra sử dụng Python 3.13.5.

### Chuẩn bị môi trường Python

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --index-url https://pypi.org/simple -r requirements-lock.txt
python -m pip check
```

Chuẩn bị `.env` theo `.env.example` và đặt đủ tám tệp nguồn tại
`data/raw/complete_journey/`.

Các bước nạp DW còn yêu cầu kết quả phân loại FMCG v1.3 tại
`data/landing/fmcg_classification_v1_3/`, gồm `product_scope.csv`
và `validation.json`.

### Khởi động PostgreSQL

```bat
docker compose up -d postgres
docker compose ps
```

Database đã triển khai có tên `fmcg_dw`, gồm các schema
`staging`, `dw`, `mart` và `audit`.

### Nạp Staging và xem trạng thái DW

```bat
python src/load_staging.py
python src/dw_run.py status --dw-load-id 2
```

ID 2 là lần nạp đã hoàn thành trên môi trường hiện tại;
môi trường khác cần dùng ID thực tế.

### Kiểm tra và chốt lần nạp

Sau khi hoàn thành nạp Dimension, Bridge và Fact, chạy các lệnh sau
với một lần nạp đang RUNNING:

```bat
python src/verify_dw.py --dw-load-id <DW_LOAD_ID>
python src/test_dw_recovery.py --dw-load-id <DW_LOAD_ID>
python src/dw_run.py finish --dw-load-id <DW_LOAD_ID>
```

Thay `<DW_LOAD_ID>` bằng số ID thực tế, không nhập dấu `<` và `>`.

Lần nạp số 2 đã SUCCESS. Không sửa trạng thái về RUNNING chỉ để
chạy lại các chương trình kiểm tra hoặc nạp dữ liệu.

Pipeline hiện được chạy từng bước, chưa có DAG Airflow điều phối.
Các lệnh trên là hướng dẫn vận hành một phần, chưa phải quy trình
tái tạo đầy đủ kho dữ liệu từ database trống.

Không đưa dữ liệu nguồn, mật khẩu, `.env` hoặc dữ liệu vận hành
lên GitHub.