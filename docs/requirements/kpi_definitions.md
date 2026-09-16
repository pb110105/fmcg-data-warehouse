# Định nghĩa KPI

## 1. Quy ước chung

Một dòng Fact tương ứng với một sản phẩm tại một cửa hàng trong một tuần. Mọi KPI phải sử dụng cùng bộ lọc thời gian, sản phẩm, cửa hàng và trạng thái khuyến mãi trên cả tử số lẫn mẫu số.

Các trường dẫn xuất:

```sql
promo_any = CASE
  WHEN feature = 1 OR display = 1 OR tpr_only = 1 THEN 1
  ELSE 0
END
```

```sql
promotion_type = CASE
  WHEN feature = 0 AND display = 0 AND tpr_only = 0 THEN 'NONE'
  WHEN feature = 0 AND display = 0 AND tpr_only = 1 THEN 'TPR_ONLY'
  WHEN feature = 0 AND display = 1 AND tpr_only = 0 THEN 'DISPLAY_ONLY'
  WHEN feature = 1 AND display = 0 AND tpr_only = 0 THEN 'FEATURE_ONLY'
  WHEN feature = 1 AND display = 1 AND tpr_only = 0 THEN 'FEATURE_DISPLAY'
  ELSE 'INVALID_COMBINATION'
END
```

Mọi phép chia phải dùng `NULLIF(mẫu_số, 0)`. Các dòng thiếu `BASE_PRICE` không tham gia KPI giảm giá. Tổng doanh số và sản lượng vẫn giữ các dòng có bất thường nếu chưa có quy tắc loại trừ được công bố.

## 2. KPI doanh số và sản lượng

| Mã | KPI | Công thức | Đơn vị | Lưu ý |
|---|---|---|---|---|
| KPI-S01 | Tổng doanh số | `SUM(spend)` | USD | Measure cộng được theo các chiều |
| KPI-S02 | Tổng số lượng bán | `SUM(units)` | Đơn vị | Measure cộng được theo các chiều |
| KPI-S03 | Tổng lượt mua có sản phẩm | `SUM(visits)` | Lượt mua–sản phẩm | Không phải số giỏ hàng duy nhất khi tổng hợp nhiều sản phẩm |
| KPI-S04 | Tổng lượt hộ gia đình–sản phẩm | `SUM(hhs)` | Lượt hộ–sản phẩm | Không phải số hộ gia đình duy nhất khi tổng hợp nhiều sản phẩm |
| KPI-S05 | Số lượng trên mỗi lượt mua | `SUM(units) / NULLIF(SUM(visits),0)` | Đơn vị/lượt | Tính trên cùng phạm vi lọc |
| KPI-S06 | Doanh số trên mỗi lượt mua | `SUM(spend) / NULLIF(SUM(visits),0)` | USD/lượt | Không diễn giải là giá trị toàn bộ giỏ hàng |
| KPI-S07 | Số lượt mua trên mỗi hộ mua sản phẩm | `SUM(visits) / NULLIF(SUM(hhs),0)` | Lượt/hộ | Chỉ có ý nghĩa ở mức sản phẩm hoặc lát cắt tương ứng |
| KPI-S08 | Tỷ trọng đóng góp doanh số | `SUM(spend của nhóm) / SUM(spend toàn bộ phạm vi)` | % | Dùng để phân tích sản phẩm, ngành hàng, cửa hàng hoặc khu vực |

## 3. KPI giá và giảm giá

| Mã | KPI | Công thức | Đơn vị | Lưu ý |
|---|---|---|---|---|
| KPI-P01 | Giá bán bình quân gia quyền | `SUM(spend) / NULLIF(SUM(units),0)` | USD/đơn vị | Phản ánh doanh thu bình quân trên một đơn vị bán; ưu tiên hơn `AVG(price)` cho tổng hợp chung |
| KPI-P02 | Giá tại kệ bình quân theo quan sát | `AVG(price_clean)` | USD | Mỗi quan sát sản phẩm–cửa hàng–tuần có trọng số bằng nhau |
| KPI-P03 | Giá cơ sở bình quân gia quyền | `SUM(base_price * units) / NULLIF(SUM(units),0)` trên dòng có `base_price` | USD/đơn vị | Loại dòng thiếu giá cơ sở khỏi cả tử và mẫu |
| KPI-P04 | Mức giảm giá tuyệt đối | `base_price - price_clean` | USD/đơn vị | Có thể âm khi giá bán cao hơn giá cơ sở |
| KPI-P05 | Tỷ lệ giảm giá theo dòng | `(base_price - price_clean) / NULLIF(base_price,0)` | % | Chỉ tính khi có cả hai mức giá và `base_price > 0` |
| KPI-P06 | Tỷ lệ giảm giá gia quyền | `1 - SUM(price_clean * units) / NULLIF(SUM(base_price * units),0)` | % | Chỉ dùng các dòng đủ giá và `units > 0` |
| KPI-P07 | Tần suất có giảm giá | `COUNT(price_clean < base_price) / COUNT(dòng đủ hai mức giá)` | % bản ghi | Khác với tỷ lệ bản ghi có cờ khuyến mãi |

## 4. KPI khuyến mãi

| Mã | KPI | Công thức | Đơn vị | Lưu ý |
|---|---|---|---|---|
| KPI-M01 | Tỷ lệ bản ghi có khuyến mãi | `COUNT(promo_any=1) / COUNT(*)` | % bản ghi | Không gọi là tỷ lệ hóa đơn có khuyến mãi |
| KPI-M02 | Tỷ trọng doanh số có khuyến mãi | `SUM(spend khi promo_any=1) / SUM(spend)` | % doanh số | Tử và mẫu dùng cùng bộ lọc |
| KPI-M03 | Tỷ trọng sản lượng có khuyến mãi | `SUM(units khi promo_any=1) / SUM(units)` | % sản lượng | Tử và mẫu dùng cùng bộ lọc |
| KPI-M04 | Doanh số bình quân trên quan sát | `AVG(spend)` | USD/quan sát | Phù hợp hơn tổng doanh số khi quy mô nhóm khuyến mãi khác nhau |
| KPI-M05 | Sản lượng bình quân trên quan sát | `AVG(units)` | Đơn vị/quan sát | Quan sát là sản phẩm–cửa hàng–tuần |
| KPI-M06 | Lượt mua bình quân trên quan sát | `AVG(visits)` | Lượt/quan sát | So sánh theo `promotion_type` |
| KPI-M07 | Chênh lệch sản lượng quan sát | `(AVG(units có KM) / NULLIF(AVG(units không KM),0)) - 1` | % | Chỉ tính khi lát cắt có cả hai trạng thái; không diễn giải nhân quả |
| KPI-M08 | Chênh lệch doanh số quan sát | `(AVG(spend có KM) / NULLIF(AVG(spend không KM),0)) - 1` | % | Chỉ là so sánh mô tả, không phải causal uplift |

## 5. Điều kiện so sánh khuyến mãi

- Luôn hiển thị số quan sát của từng nhóm khuyến mãi.
- Ưu tiên so sánh trong cùng sản phẩm, cửa hàng hoặc nhóm phân tích tương đương.
- Không chỉ so sánh tổng doanh số vì số tuần và số sản phẩm của các nhóm khác nhau.
- Có thể trình bày trung vị cùng trung bình khi phân phối bị lệch bởi ngoại lệ.
- Không gọi KPI-M07 hoặc KPI-M08 là tác động nhân quả của khuyến mãi.

## 6. Quy tắc thời gian

- Tuần sử dụng trực tiếp `WEEK_END_DATE`.
- Tháng, quý và năm được xác định từ ngày kết thúc tuần.
- Một tuần chỉ thuộc một tháng hoặc quý theo `WEEK_END_DATE`; dữ liệu không cho phép phân bổ chính xác doanh số theo từng ngày.

