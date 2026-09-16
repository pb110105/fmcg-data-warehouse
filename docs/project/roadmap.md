# Lộ trình thực hiện dự án

## Giai đoạn 1 – Chuẩn bị đề tài và dữ liệu

- Chốt tên đề tài, mục tiêu và phạm vi.
- Khảo sát nguồn, cấu trúc, grain và chất lượng dữ liệu.
- Hoàn thiện Data Dictionary, câu hỏi nghiệp vụ và KPI.
- Chốt kiến trúc và công nghệ ở mức tổng thể.

Đầu ra: bộ tài liệu trong `docs/dataset`, `docs/requirements` và `docs/architecture`.

## Giai đoạn 2 – Thiết kế dữ liệu

- Thiết kế Landing và Staging.
- Thiết kế mô hình hình sao chi tiết.
- Xác định surrogate key, business key và quan hệ Fact–Dimension.
- Lập source-to-target mapping.
- Thiết kế bảng audit và quy tắc kiểm tra chất lượng.

Đầu ra: ERD, Data Dictionary đích, source-to-target mapping và DDL dự thảo.

## Giai đoạn 3 – Khởi tạo môi trường

- Xây dựng Docker Compose.
- Khởi tạo PostgreSQL và các schema.
- Tạo bảng Staging, Data Warehouse, Data Mart và audit.
- Chuẩn bị cấu trúc project Python và cấu hình môi trường.

Đầu ra: môi trường chạy cục bộ và database rỗng đúng thiết kế.

## Giai đoạn 4 – Xây dựng ETL

- Trích xuất Excel vào Landing/Staging.
- Làm sạch và chuẩn hóa dữ liệu.
- Xử lý mâu thuẫn cửa hàng, giá thiếu và các cờ chất lượng.
- Nạp Dimension và Fact.
- Bảo đảm pipeline có thể chạy lại mà không nhân đôi dữ liệu.

Đầu ra: pipeline ETL hoàn chỉnh và dữ liệu được nạp vào kho.

## Giai đoạn 5 – Điều phối ETL bằng Airflow

- Xây dựng DAG ETL.
- Thiết lập thứ tự thực hiện các tác vụ.
- Cấu hình logging và xử lý lỗi.
- Kiểm tra khả năng chạy lại pipeline.

Đầu ra: DAG Airflow vận hành được và pipeline có thể theo dõi.

## Giai đoạn 6 – Data Mart, phân tích và Power BI

- Xây dựng bốn Data Mart.
- Viết và kiểm tra truy vấn KPI.
- Kết nối Power BI với PostgreSQL.
- Xây dựng dashboard và bộ lọc.
- Đối chiếu chỉ số Power BI với kết quả SQL.

Đầu ra: Data Mart, kết quả phân tích và dashboard Power BI.

## Giai đoạn 7 – Đánh giá và hoàn thiện báo cáo

- Đánh giá ETL, chất lượng dữ liệu và hiệu năng truy vấn.
- Đối soát dữ liệu nguồn với kho dữ liệu.
- Đồng bộ báo cáo với hệ thống thực tế.
- Hoàn thiện phụ lục, slide và kịch bản bảo vệ.

Đầu ra: kết quả đánh giá, báo cáo tiểu luận và slide bảo vệ.
