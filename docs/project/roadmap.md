# Lộ trình thực hiện

Đề tài: Xây dựng hệ thống kho dữ liệu bán lẻ FMCG phục vụ phân tích doanh số, giá bán và hiệu quả khuyến mãi.

## 1. Các giai đoạn

| Giai đoạn | Nội dung chính | Trạng thái |
|---|---|---|
| 1. Chuẩn bị | Khảo sát nguồn, phân loại FMCG, xác minh thời gian, xác định yêu cầu và KPI | Đã có kết quả chính; Hoàn thành |
| 2. Thiết kế | Thiết kế Fact–Dimension, Staging, mapping và DDL | Đã soạn tài liệu và SQL; đang rà soát, chưa kiểm thử DDL |
| 3. Khởi tạo môi trường | Thiết lập Docker Compose, PostgreSQL và chạy DDL | Chưa bắt đầu |
| 4. Xây dựng ETL | Nạp nguồn, làm sạch, nạp kho dữ liệu và đối soát | Chưa bắt đầu |
| 5. Điều phối | Xây dựng DAG Airflow, logging và kiểm tra chạy lại | Chưa bắt đầu |
| 6. Phân tích | Xây dựng Data Mart, KPI và Power BI | Chưa bắt đầu |
| 7. Hoàn thiện | Đánh giá hệ thống, hoàn thiện báo cáo và chuẩn bị bảo vệ | Chưa bắt đầu |

## 2. Công việc tiếp theo

1. Đồng bộ README, kiến trúc, mapping và KPI với thiết kế hiện tại.
2. Khởi tạo môi trường PostgreSQL.
3. Chạy bốn file DDL theo thứ tự và kiểm tra bảng, khóa, ràng buộc.
4. Bắt đầu xây dựng ETL nạp dữ liệu vào Staging.

## 3. Nguyên tắc cập nhật

- Commit và push sau mỗi phần công việc đã kiểm tra.
- Phân biệt trạng thái đã viết, đã chạy và đã đối soát.
- Nhóm REVIEW chưa được đưa vào KPI FMCG.
- Các công thức giá chưa xác minh tiếp tục để ngoài KPI chính thức.