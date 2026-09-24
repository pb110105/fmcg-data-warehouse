# Phạm vi đề tài

## 1. Tên đề tài

Xây dựng hệ thống kho dữ liệu bán lẻ FMCG phục vụ phân tích doanh số, giá bán và hiệu quả khuyến mãi.

## 2. Phạm vi dữ liệu

- Sử dụng Complete Journey của dunnhumby, phiên bản từ package `completejourney`.
- Gồm tám bảng: transactions, products, demographics, promotions, campaigns, campaign_descriptions, coupons và coupon_redemptions.
- Phân tích bán hàng và hỗ trợ khuyến mãi trên các sản phẩm được xác định thuộc FMCG theo `docs/dataset/fmcg_scope.md`.
- Phân tích chiến dịch và đổi coupon trên phạm vi dữ liệu nguồn; không quy đổi trực tiếp thành doanh số FMCG.
- Quy mô dữ liệu sau lọc FMCG được xác định khi hoàn tất phân loại sản phẩm.

## 3. Nội dung thực hiện

- Khảo sát dữ liệu và xây dựng quy tắc kiểm tra chất lượng.
- Thiết kế Staging, kho dữ liệu Fact–Dimension và Data Mart.
- Xây dựng ETL, nhật ký xử lý và đối soát dữ liệu.
- Điều phối pipeline bằng Apache Airflow.
- Phân tích doanh số, sản lượng, giá trị bán bình quân trên đơn vị và các khoản giảm giá.
- So sánh kết quả bán hàng theo điều kiện trưng bày, quảng cáo.
- Thống kê tiếp nhận chiến dịch và đổi coupon.
- Xây dựng dashboard Power BI và đánh giá hệ thống.

## 4. Nội dung ngoài phạm vi

- Dự báo, Machine Learning, RFM và khai phá giỏ hàng.
- Tính lợi nhuận hoặc ROI do thiếu dữ liệu chi phí.
- Khẳng định quan hệ nhân quả giữa khuyến mãi và doanh số.
- Gán trực tiếp giao dịch bán hàng cho chiến dịch khi không có khóa liên kết.
- Phân tích địa lý cửa hàng do nguồn hiện tại không có thông tin vị trí.

## 5. Công nghệ

Python, pandas, pyreadr, PostgreSQL, Apache Airflow, Docker Compose và Power BI; triển khai trên môi trường cục bộ.

## 6. Giới hạn diễn giải

- Chỉ cộng sản lượng giữa các sản phẩm có đơn vị đo tương thích.
- Công thức giá và giảm giá phải được xác minh trước khi triển khai KPI.
- Kết quả chỉ phản ánh dữ liệu được cung cấp, không đại diện cho toàn bộ thị trường FMCG hoặc thị trường Việt Nam.