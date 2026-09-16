# Phạm vi dự án

## 1. Đối tượng

Đối tượng của đề tài là hệ thống kho dữ liệu phục vụ phân tích hoạt động bán lẻ FMCG. Đề tài tập trung vào quá trình tiếp nhận, làm sạch, chuẩn hóa, tích hợp và tổ chức dữ liệu theo mô hình đa chiều.

Dữ liệu nghiên cứu gồm dữ liệu bán hàng theo tuần, sản phẩm, cửa hàng, giá bán, giá cơ sở và ba hình thức hỗ trợ khuyến mãi. Trên cơ sở đó, hệ thống cung cấp chỉ số về doanh số, sản lượng, giá bán, mức giảm giá, sản phẩm, cửa hàng và khuyến mãi.

## 2. Phạm vi dữ liệu

- Bộ dữ liệu: dunnhumby *Breakfast at the Frat*.
- Thời gian: 156 tuần, từ 14/01/2009 đến 04/01/2012.
- Grain: sản phẩm–cửa hàng–tuần.
- Quy mô: 524.950 bản ghi bán hàng, 77 cửa hàng và 55 sản phẩm phát sinh bán hàng.
- Ngành hàng: ngũ cốc đóng hộp, pizza đông lạnh, bánh pretzel và nước súc miệng.

## 3. Trong phạm vi

- Khảo sát cấu trúc và đánh giá chất lượng dữ liệu nguồn.
- Xây dựng vùng Landing và Staging.
- Xây dựng quy trình ETL để làm sạch, chuẩn hóa, tích hợp và nạp dữ liệu.
- Thiết kế kho dữ liệu theo mô hình hình sao.
- Xây dựng bảng kiểm soát chất lượng và log ETL.
- Xây dựng Data Mart doanh số, giá, khuyến mãi, sản phẩm và cửa hàng.
- Phân tích doanh số và sản lượng theo thời gian, sản phẩm, cửa hàng và khu vực.
- Phân tích giá bán và mức giảm giá.
- So sánh kết quả bán hàng giữa các điều kiện khuyến mãi.
- Xây dựng dashboard Power BI.
- Đối soát dữ liệu, đánh giá ETL, chất lượng dữ liệu và hiệu năng truy vấn.

## 4. Ngoài phạm vi

- Dự báo theo thời gian.
- Machine Learning.
- Khai phá giỏ hàng.
- RFM và phân tích khách hàng cá nhân.
- Phân tích lợi nhuận do không có giá vốn.
- Khẳng định quan hệ nhân quả giữa khuyến mãi và doanh số.
- Khái quát kết quả cho toàn bộ thị trường FMCG hoặc thị trường Việt Nam.

## 5. Phạm vi công nghệ

Hệ thống chạy cục bộ bằng Docker Compose. Python và pandas xử lý dữ liệu; PostgreSQL lưu Staging, Data Warehouse, Data Mart và audit; Apache Airflow điều phối pipeline; Power BI trực quan hóa kết quả.

