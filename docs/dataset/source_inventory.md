# Kiểm kê dữ liệu nguồn

## 1. File nguồn

| File | Định dạng | Kích thước | Vai trò |
|---|---|---:|---|
| `dunnhumby - Breakfast at the Frat.xlsx` | XLSX | 31.634.601 byte | Dữ liệu bán hàng, sản phẩm, cửa hàng và Glossary |
| `dunnhumby - Breakfast at the Frat User Guide.pdf` | PDF | 381.475 byte | Mô tả dữ liệu và gợi ý phân tích |

Các sheet dữ liệu đặt tiêu đề cột ở dòng thứ hai. Sheet `Glossary` đặt tiêu đề ở dòng thứ tư. Khi đọc bằng pandas cần sử dụng `header=1` cho ba sheet dữ liệu và `header=3` cho `Glossary`. Các dòng Excel chỉ có định dạng nhưng rỗng không được tính là bản ghi.

## 2. Danh sách sheet

| Sheet | Số bản ghi | Số cột | Vai trò | Khóa hoặc grain |
|---|---:|---:|---|---|
| `Glossary` | 24 | 4 | Giải thích thuộc tính | Không có khóa nghiệp vụ |
| `dh Store Lookup` | 79 | 9 | Tra cứu cửa hàng | `STORE_ID`; có 77 giá trị phân biệt |
| `dh Products Lookup` | 58 | 6 | Tra cứu sản phẩm | `UPC`; 58 giá trị phân biệt |
| `dh Transaction Data` | 524.950 | 12 | Kết quả bán hàng hàng tuần | `WEEK_END_DATE + STORE_NUM + UPC` |

## 3. Quan hệ dữ liệu

| Bảng con | Cột liên kết | Bảng cha | Cột liên kết | Kết quả khảo sát |
|---|---|---|---|---|
| `dh Transaction Data` | `UPC` | `dh Products Lookup` | `UPC` | Không có khóa ngoại không khớp |
| `dh Transaction Data` | `STORE_NUM` | `dh Store Lookup` | `STORE_ID` | Không có mã không khớp, nhưng bảng cửa hàng có hai mã bị lặp |

Lưu ý: tên khóa cửa hàng không đồng nhất giữa hai sheet. Bảng giao dịch dùng `STORE_NUM`, trong khi bảng cửa hàng dùng `STORE_ID`. ETL phải ánh xạ hai cột này theo quan hệ `STORE_NUM = STORE_ID`.

## 4. Quy mô giao dịch

| Thuộc tính | Giá trị |
|---|---:|
| Số bản ghi | 524.950 |
| Số tuần | 156 |
| Ngày đầu | 14/01/2009 |
| Ngày cuối | 04/01/2012 |
| Số cửa hàng | 77 |
| Số sản phẩm có bán hàng | 55 |
| Tổng số lượng bán | 10.293.354 |
| Tổng lượt mua có sản phẩm | 9.012.000 |
| Tổng lượt hộ gia đình–sản phẩm | 8.807.234 |
| Tổng doanh số | 27.927.722,58 USD |

Các tổng `VISITS` và `HHS` là tổng ở mức sản phẩm, có khả năng đếm lặp một giỏ hàng hoặc hộ gia đình khi phân tích đồng thời nhiều sản phẩm.

## 5. Thông tin sản phẩm

| Nhóm ngành hàng nguồn | Số sản phẩm trong lookup |
|---|---:|
| `BAG SNACKS` | 15 |
| `COLD CEREAL` | 15 |
| `FROZEN PIZZA` | 15 |
| `ORAL HYGIENE PRODUCTS` | 13 |

Bảng sản phẩm có bảy tiểu nhóm và 17 nhà sản xuất. Ba sản phẩm của `HOME RUN` có trong lookup nhưng không xuất hiện trong dữ liệu bán hàng. Các sản phẩm này vẫn thuộc phạm vi bảng chiều sản phẩm.

## 6. Thông tin cửa hàng

| Bang | Số cửa hàng phân biệt |
|---|---:|
| Texas (`TX`) | 41 |
| Ohio (`OH`) | 31 |
| Kentucky (`KY`) | 4 |
| Indiana (`IN`) | 1 |

Sheet cửa hàng có 79 dòng nhưng chỉ có 77 mã cửa hàng. Hai mã `4503` và `17627` xuất hiện hai lần với cùng thông tin cơ bản nhưng khác `SEG_VALUE_NAME`: một dòng là `MAINSTREAM`, dòng còn lại là `UPSCALE`. Nếu join trực tiếp, 13.693 bản ghi giao dịch liên quan sẽ bị nhân đôi.

## 7. Trạng thái khuyến mãi

| FEATURE | DISPLAY | TPR_ONLY | Trạng thái | Số bản ghi |
|---:|---:|---:|---|---:|
| 0 | 0 | 0 | Không khuyến mãi | 375.564 |
| 0 | 0 | 1 | Chỉ giảm giá tạm thời | 70.734 |
| 0 | 1 | 0 | Chỉ trưng bày | 34.401 |
| 1 | 0 | 0 | Chỉ quảng cáo | 20.837 |
| 1 | 1 | 0 | Quảng cáo và trưng bày | 23.414 |

Có 149.386 bản ghi nhận ít nhất một hình thức hỗ trợ khuyến mãi, chiếm khoảng 28,46% dữ liệu giao dịch. Không xuất hiện tổ hợp khuyến mãi nào khác ngoài năm trạng thái trên.

