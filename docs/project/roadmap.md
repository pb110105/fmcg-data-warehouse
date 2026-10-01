# Lộ trình thực hiện

Đề tài: Xây dựng hệ thống kho dữ liệu bán lẻ FMCG phục vụ phân tích
doanh số, giá bán và hiệu quả khuyến mãi.

Ngày cập nhật: 01/10/2026.

## 1. Các giai đoạn

| Giai đoạn | Nội dung chính | Trạng thái |
|---|---|---|
| 1. Chuẩn bị | Khảo sát nguồn, phân loại FMCG, xác minh thời gian và KPI | Hoàn thành |
| 2. Thiết kế | Fact–Dimension, Staging, mapping và DDL | Hoàn thành |
| 3. Khởi tạo môi trường | Python, Docker Compose, PostgreSQL và kiểm tra DDL | Hoàn thành |
| 4. Xây dựng ETL | Nạp Staging, Dimension, Bridge, Fact và đối soát | Hoàn thành |
| 5. Điều phối | DAG Airflow, phụ thuộc tác vụ, logging và retry | Chưa bắt đầu |
| 6. Phân tích | Data Mart, KPI và Power BI | Chưa bắt đầu |
| 7. Hoàn thiện | Đánh giá, báo cáo và chuẩn bị bảo vệ | Chưa bắt đầu |

## 2. Kết quả Giai đoạn 4

- Nguồn Staging: `etl_batch_id=1`, trạng thái SUCCESS.
- Lần nạp DW: `dw_load_id=2`, trạng thái SUCCESS.
- Phiên bản pipeline: `dw-1.0`.
- Phiên bản FMCG: `1.3-cosmetics-and-exclusions`.
- Hoàn thành nạp 7 Dimension, 2 Bridge và 3 Fact.

| Kiểm tra | Kết quả |
|---|---|
| Đối soát DW | 89 PASS, 0 lỗi |
| Khóa ngoại | Không phát hiện khóa mồ côi |
| Số lượng và các khoản tiền | Khớp nguồn theo quy tắc chuẩn hóa |
| Nối bán hàng–khuyến mãi | Không nhân dòng hoặc tăng số đo |
| Chạy lại các bước nạp đã thử | Không chèn thêm dữ liệu |
| Cơ chế nạp dùng chung trên 7 Dimension | Giữ nguyên khóa và toàn bộ dòng |
| Lỗi giả lập trước commit | Rollback về trạng thái ban đầu |
| Thử phục hồi một dòng coupon | Phục hồi thành công; chạy thêm lần nữa không chèn trùng |

Kiểm thử phục hồi sử dụng hàm nạp dùng chung và transaction;
chưa kiểm thử tắt Docker đột ngột hoặc mất điện.

### Số liệu DW sau nạp

| Bảng | Số dòng |
|---|---:|
| `dim_date` | 472 |
| `dim_week` | 53 |
| `dim_product` | 92.351 |
| `dim_household` | 2.469 |
| `dim_store` | 457 |
| `dim_campaign` | 27 |
| `dim_coupon` | 1.197 |
| `bridge_campaign_household` | 6.589 |
| `bridge_coupon_product` | 111.332 |
| `fact_sales` | 1.271.042 |
| `fact_promotion_weekly` | 17.485.242 |
| `fact_coupon_redemption` | 2.102 |

### Tổng số đo Fact Sales

| Số đo | Giá trị |
|---|---:|
| `quantity` | 1.676.406 |
| `sales_value` | 3.419.948,46 |
| `retail_disc` | 710.911,57 |
| `coupon_disc` | 16.824,58 |
| `coupon_match_disc` | 4.358,46 |

Các số đo tiền sử dụng USD. Tổng quantity là tổng giá trị số lượng
nguồn, không đại diện cho một đơn vị vật lý đồng nhất giữa sản phẩm.

## 3. Lưu ý khi phân tích

- Chỉ IN_SCOPE được đưa vào Fact Sales và Fact Promotion Weekly.
- REVIEW tiếp tục nằm ngoài KPI FMCG.
- Fact Coupon Redemption giữ phạm vi toàn nguồn.
- Có 971.514 dòng bán hàng không khớp thông tin khuyến mãi.
  Không tự xem các dòng này là không khuyến mãi.
- Chưa dùng các công thức giá trước giảm, tiền khách thực trả
  và tỷ lệ giảm giá kết hợp chưa được xác minh.
- Không diễn giải chênh lệch bán hàng thành tác động nhân quả.

## 4. Công việc tiếp theo

1. Hoàn tất commit và push mã nguồn, tài liệu Giai đoạn 4.
2. Chuẩn bị môi trường Apache Airflow.
3. Tổ chức các bước ETL thành DAG với phụ thuộc rõ ràng.
4. Xử lý việc tái sử dụng batch, lần nạp DW và trạng thái SUCCESS.
5. Kiểm tra chạy DAG, retry và nhật ký trước khi xây dựng Data Mart.