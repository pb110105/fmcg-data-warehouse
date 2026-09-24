# Kế hoạch thực hiện

## 1. Người thực hiện

- Sinh viên: Phạm Trần Quốc Bảo.
- MSSV: 23133006.
- Hình thức: thực hiện cá nhân.

## 2. Đề tài

Xây dựng hệ thống kho dữ liệu bán lẻ FMCG phục vụ phân tích doanh số, giá bán và hiệu quả khuyến mãi.

Dữ liệu sử dụng: Complete Journey, phiên bản từ package `completejourney`.

## 3. Các giai đoạn thực hiện

| Giai đoạn | Công việc chính |
|---|---|
| 1. Chuẩn bị | Khảo sát dữ liệu, xác định phạm vi FMCG, câu hỏi nghiệp vụ và KPI |
| 2. Thiết kế | Thiết kế Staging, Fact–Dimension, ánh xạ nguồn–đích và quy tắc kiểm tra dữ liệu |
| 3. Khởi tạo môi trường | Thiết lập Docker Compose, PostgreSQL và các schema |
| 4. Xây dựng ETL | Trích xuất, làm sạch, phân loại FMCG, nạp dữ liệu và đối soát |
| 5. Điều phối | Xây dựng DAG Airflow, ghi nhật ký và kiểm tra khả năng chạy lại |
| 6. Phân tích | Xây dựng Data Mart và dashboard Power BI |
| 7. Hoàn thiện | Đánh giá hệ thống, hoàn thiện báo cáo và chuẩn bị bảo vệ |

## 4. Công việc trước mắt

- Hoàn thiện tài liệu Giai đoạn 1 theo Complete Journey.
- Kiểm tra và chốt quy tắc phân loại sản phẩm FMCG.
- Xác minh cách diễn giải thời gian và các trường giá, giảm giá.
- Thống nhất câu hỏi nghiệp vụ, KPI và kiến trúc trước khi thiết kế chi tiết.

## 5. Theo dõi tiến độ

- Cập nhật trạng thái từng giai đoạn trong `docs/project/roadmap.md`.
- Cập nhật README khi có thay đổi về phạm vi hoặc kết quả thực hiện.
- Commit và push lên GitHub sau mỗi phần công việc hoàn thành.
- Chỉ đánh dấu hoàn thành khi đã có sản phẩm và kiểm tra tương ứng.