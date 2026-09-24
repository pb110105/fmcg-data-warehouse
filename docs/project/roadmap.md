# Lộ trình thực hiện

Đề tài: Xây dựng hệ thống kho dữ liệu bán lẻ FMCG phục vụ phân tích doanh số, giá bán và hiệu quả khuyến mãi.

## 1. Các giai đoạn

| Giai đoạn | Nội dung chính | Sản phẩm đầu ra | Trạng thái |
|---|---|---|---|
| 1. Chuẩn bị | Khảo sát Complete Journey, xác định phạm vi FMCG, yêu cầu và KPI | Hồ sơ dữ liệu, phạm vi, câu hỏi nghiệp vụ, KPI và kiến trúc đề xuất | Đang hoàn thiện |
| 2. Thiết kế | Thiết kế Staging, Fact–Dimension, ánh xạ nguồn–đích và kiểm tra chất lượng | Mô hình dữ liệu, mapping và DDL | Chưa bắt đầu |
| 3. Khởi tạo môi trường | Thiết lập Docker Compose, PostgreSQL và các schema | Môi trường chạy cục bộ và cấu trúc cơ sở dữ liệu | Chưa bắt đầu |
| 4. Xây dựng ETL | Trích xuất, làm sạch, phân loại FMCG, nạp và đối soát | Chương trình ETL, dữ liệu trong kho và kết quả kiểm tra | Chưa bắt đầu |
| 5. Điều phối | Xây dựng DAG Airflow, ghi nhật ký và kiểm tra chạy lại | Pipeline được điều phối và có thể theo dõi | Chưa bắt đầu |
| 6. Phân tích | Xây dựng Data Mart, KPI và Power BI | Data Mart và dashboard | Chưa bắt đầu |
| 7. Hoàn thiện | Đánh giá hệ thống, viết báo cáo và chuẩn bị bảo vệ | Báo cáo, slide và hướng dẫn vận hành | Chưa bắt đầu |

## 2. Công việc cần chốt ở Giai đoạn 1

- Đồng bộ tài liệu theo bộ dữ liệu Complete Journey.
- Kiểm tra và chốt quy tắc phân loại sản phẩm FMCG.
- Xác minh cách diễn giải thời gian, giá và các khoản giảm giá.
- Rà soát sự thống nhất giữa phạm vi, câu hỏi nghiệp vụ và KPI.

## 3. Cập nhật tiến độ

- Cập nhật trạng thái khi hoàn thành từng phần công việc.
- Commit và push tài liệu, mã nguồn lên GitHub sau mỗi mốc hoàn thành.
- Chỉ đánh dấu hoàn thành khi sản phẩm đầu ra đã được kiểm tra.