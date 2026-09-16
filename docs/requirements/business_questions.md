# Câu hỏi nghiệp vụ

## 1. Người sử dụng giả định

- Nhà quản lý bán hàng.
- Nhà quản lý ngành hàng.
- Nhà quản lý cửa hàng.
- Bộ phận quản lý giá và khuyến mãi.
- Bộ phận Business Intelligence.

## 2. Câu hỏi về doanh số và sản lượng

| Mã | Câu hỏi |
|---|---|
| BQ-S01 | Tổng doanh số và số lượng bán trong toàn bộ thời gian nghiên cứu là bao nhiêu? |
| BQ-S02 | Doanh số và sản lượng biến động như thế nào theo tuần, tháng, quý và năm? |
| BQ-S03 | Sản phẩm, ngành hàng và nhà sản xuất nào đóng góp nhiều nhất hoặc ít nhất vào doanh số? |
| BQ-S04 | Doanh số và sản lượng phân bổ như thế nào theo cửa hàng, thành phố, bang và phân khúc cửa hàng? |
| BQ-S05 | Tỷ trọng đóng góp doanh số của từng sản phẩm, ngành hàng, cửa hàng và khu vực là bao nhiêu? |

## 3. Câu hỏi về giá bán

| Mã | Câu hỏi |
|---|---|
| BQ-P01 | Giá bán thực tế và giá cơ sở nằm trong khoảng nào đối với từng sản phẩm và ngành hàng? |
| BQ-P02 | Giá bán bình quân gia quyền khác nhau như thế nào theo sản phẩm, ngành hàng, cửa hàng và thời gian? |
| BQ-P03 | Sản phẩm hoặc ngành hàng nào có mức giảm giá và tần suất giảm giá cao nhất? |
| BQ-P04 | Doanh số và sản lượng quan sát được khác nhau như thế nào giữa các nhóm mức giảm giá? |
| BQ-P05 | Mối liên hệ quan sát được giữa giá bán, mức giảm giá, sản lượng và doanh số có khác nhau giữa các ngành hàng hay không? |

## 4. Câu hỏi về khuyến mãi

| Mã | Câu hỏi |
|---|---|
| BQ-M01 | Tỷ lệ bản ghi bán hàng nhận ít nhất một hình thức hỗ trợ khuyến mãi là bao nhiêu? |
| BQ-M02 | Bao nhiêu phần trăm doanh số và sản lượng phát sinh trong điều kiện có khuyến mãi? |
| BQ-M03 | Doanh số, sản lượng và số lượng trên mỗi lượt mua khác nhau như thế nào giữa điều kiện có và không có khuyến mãi? |
| BQ-M04 | Kết quả bán hàng quan sát được khác nhau như thế nào giữa TPR, trưng bày, quảng cáo và quảng cáo kết hợp trưng bày? |
| BQ-M05 | Trạng thái khuyến mãi nào có doanh số và sản lượng bình quân trên một quan sát sản phẩm–cửa hàng–tuần cao nhất? |
| BQ-M06 | Kết quả bán hàng của quảng cáo kết hợp trưng bày khác với từng hình thức riêng lẻ như thế nào? |
| BQ-M07 | Chênh lệch kết quả bán hàng theo trạng thái khuyến mãi thay đổi như thế nào giữa các sản phẩm, ngành hàng, khu vực và phân khúc cửa hàng? |

## 5. Câu hỏi về sản phẩm và cửa hàng

| Mã | Câu hỏi |
|---|---|
| BQ-PS01 | Những sản phẩm nào có doanh số và sản lượng cao nhất hoặc thấp nhất? |
| BQ-PS02 | Hiệu quả bán hàng của cùng một sản phẩm khác nhau như thế nào giữa các cửa hàng và phân khúc cửa hàng? |
| BQ-PS03 | Cửa hàng nào đóng góp nhiều nhất vào doanh số của từng ngành hàng? |
| BQ-PS04 | Những tổ hợp sản phẩm–cửa hàng nào có doanh số hoặc sản lượng thấp cần được chú ý? |
| BQ-PS05 | Sản phẩm nào có tỷ trọng doanh số phát sinh trong điều kiện khuyến mãi cao nhất? |
| BQ-PS06 | Quy mô cửa hàng, số giỏ hàng trung bình và phân khúc cửa hàng có mối liên hệ quan sát được như thế nào với kết quả bán hàng? |

## 6. Giới hạn diễn giải

- Không gọi tổng `VISITS` của nhiều sản phẩm là số giỏ hàng duy nhất.
- Không gọi tổng `HHS` của nhiều sản phẩm là số khách hàng hoặc hộ gia đình duy nhất.
- Không sử dụng các câu hỏi trên để khẳng định khuyến mãi gây ra thay đổi doanh số.
- Phân tích theo tháng sử dụng tháng chứa `WEEK_END_DATE`; dữ liệu không thể hiện ngày bán thực tế.
- Mọi so sánh khuyến mãi phải trình bày cả quy mô mẫu và KPI bình quân, không chỉ tổng doanh số.

## 7. Ánh xạ đầu ra

| Nhóm câu hỏi | KPI chính | Chiều phân tích | Data Mart dự kiến | Dashboard dự kiến |
|---|---|---|---|---|
| BQ-S | Doanh số, sản lượng, tỷ trọng đóng góp | Thời gian, sản phẩm, cửa hàng | `mart_sales_overview` | Tổng quan doanh số |
| BQ-P | Giá bình quân, giá cơ sở, mức giảm giá | Thời gian, sản phẩm, cửa hàng | `mart_price_analysis` | Giá bán và mức giảm giá |
| BQ-M | Tỷ trọng khuyến mãi, KPI bình quân, chênh lệch quan sát | Khuyến mãi, sản phẩm, cửa hàng | `mart_promotion_analysis` | Khuyến mãi |
| BQ-PS | Doanh số, sản lượng, đóng góp | Sản phẩm, cửa hàng, khu vực | `mart_product_store` | Sản phẩm và cửa hàng |

