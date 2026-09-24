# Phạm vi sản phẩm FMCG

## 1. Mục đích và phiên bản

Xác định sản phẩm được sử dụng để phân tích doanh số, giá bán và khuyến mãi trong bộ Complete Journey.

- Phiên bản quy tắc: `1.3-cosmetics-and-exclusions`.
- Mã xử lý: `src/classify_fmcg.py`.
- Nguồn đầu vào: `products.rda` và `transactions.rds`.
- Trạng thái: đã chạy phân loại và đối soát; tạm cố định phạm vi phiên bản 1.3 để tiếp tục thiết kế.

Đây là phạm vi nghiên cứu do project lựa chọn, không phải nhãn FMCG do nguồn cung cấp.

## 2. Trạng thái phân loại

| Trạng thái | Ý nghĩa |
|---|---|
| `IN_SCOPE` | Được chọn vào phạm vi phân tích FMCG |
| `OUT_OF_SCOPE` | Ngoài phạm vi nghiên cứu đã chọn |
| `REVIEW` | Chưa đủ thông tin hoặc chưa có quy tắc xác nhận |

KPI FMCG chỉ sử dụng `IN_SCOPE`. Hai nhóm còn lại vẫn được giữ để truy vết và đối soát, không xóa khỏi dữ liệu nguồn.

## 3. Quy tắc đang áp dụng

### 3.1. Chuẩn hóa nhãn

- Giữ nguyên các thuộc tính nguồn.
- Khi đối chiếu, loại khoảng trắng đầu/cuối và chuyển nhãn sang chữ hoa.
- So khớp chính xác nhãn; không phân loại bằng tìm kiếm từ khóa gần đúng.
- Các quy tắc bổ sung sử dụng đủ `department`, `product_category` và `product_type`.

### 3.2. Nhóm được chọn theo department

Các department sau được gán `IN_SCOPE` khi có đủ category và type, trừ các ngoại lệ cần xem xét:

- `GROCERY`
- `FROZEN GROCERY`
- `PRODUCE`
- `MEAT`
- `MEAT-PCKGD`
- `SEAFOOD`
- `SEAFOOD-PCKGD`
- `DELI`
- `PASTRY`

Phạm vi bao gồm thực phẩm tươi, thực phẩm chế biến, đồ uống và hàng tiêu dùng thường xuyên trong nhóm tạp hóa. Thức ăn thú nuôi và cát vệ sinh trong `GROCERY` được giữ trong phạm vi.

Các category ngoại lệ được giữ `REVIEW`:

- `COUPON/MISC ITEMS`
- `COUPON`
- `BOTTLE DEPOSITS`
- `DELI SUPPLIES`
- `MEAT SUPPLIES`
- `PROD SUPPLIES`
- `PET CARE SUPPLIES`
- `MISCELLANEOUS`
- `MEAT - MISC`
- `SEAFOOD - MISC`
- `PKG.SEAFOOD MISC`
- `SEASONAL`
- `LIQUOR`
- `BEERS/ALES`
- `DOMESTIC WINE`
- `MISC WINE`
- `IMPORTED WINE`

Các nhóm này có thể chứa hàng hóa hợp lệ, vật tư, khoản điều chỉnh hoặc nhãn chưa rõ; không tự động xem toàn bộ là lỗi.

### 3.3. Quy tắc bổ sung theo category/type

| Phiên bản | Nội dung bổ sung |
|---|---|
| 1.1 | Một số sản phẩm chăm sóc cá nhân trong `DRUG GM`: xà phòng, chăm sóc tóc, răng miệng, khử mùi, tã và vệ sinh cá nhân |
| 1.2 | Các loại thực phẩm và đồ uống được chọn trong `NUTRITION` |
| 1.3 | Một số mỹ phẩm tiêu hao trong `COSMETICS`; xác định thêm dụng cụ lâu bền, phụ kiện và dịch vụ ngoài phạm vi |

Danh sách tổ hợp chính xác được khai báo trong script:

- `PERSONAL_CARE_TYPES`
- `NUTRITION_TYPES`
- `COSMETICS_TYPES`
- `EXCLUDED_TYPES`

Không đưa toàn bộ department hoặc category vào phạm vi chỉ vì có một số sản phẩm phù hợp. Các nhãn chỉ thể hiện thương hiệu, thuốc, sản phẩm bổ sung hoặc mô tả chưa rõ tiếp tục giữ `REVIEW` nếu chưa có quy tắc.

### 3.4. Nhóm ngoài phạm vi theo department

Các department sau được gán `OUT_OF_SCOPE`:

- `FUEL`
- `FLORAL`
- `GARDEN CENTER`
- `RESTAURANT`
- `TRAVEL & LEISURE`
- `PHOTO & VIDEO`
- `TOYS`
- `POSTAL CENTER`
- `AUTOMOTIVE`
- `ELECT &PLUMBING`
- `HOUSEWARES`
- `CNTRL/STORE SUP`
- `CHARITABLE CONT`
- `GM MERCH EXP`
- `COUPON`
- `SPIRITS`

Đây là quyết định giới hạn project, không khẳng định mọi hàng hóa trong các nhóm này đều nằm ngoài mọi định nghĩa FMCG.

### 3.5. Trường hợp chưa xác định

- Department chưa có quy tắc: giữ `REVIEW`.
- Nhóm được chọn nhưng thiếu category hoặc type: giữ `REVIEW`.
- Mã sản phẩm giao dịch không có trong lookup: tạo kết quả `REVIEW` riêng cho mã đó.
- Thiếu `package_size` không tự động loại sản phẩm khỏi FMCG; điều kiện tính KPI theo đơn vị được kiểm tra riêng.

Các quy tắc chi tiết hiện chỉ cập nhật sản phẩm đang `REVIEW`. Khi bổ sung quy tắc mới, cần kiểm tra tránh tổ hợp trùng hoặc mâu thuẫn.

## 4. Kết quả phiên bản 1.3

| Trạng thái | Sản phẩm trong lookup | Sản phẩm có giao dịch | Dòng giao dịch | Tổng sales_value (USD) |
|---|---:|---:|---:|---:|
| `IN_SCOPE` | 55.568 | 41.948 | 1.271.042 | 3.419.948,46 |
| `OUT_OF_SCOPE` | 2.088 | 1.506 | 20.691 | 395.944,98 |
| `REVIEW` | 34.675 | 25.055 | 177.574 | 780.146,14 |
| **Tổng** | **92.331** | **68.509** | **1.469.307** | **4.596.039,58** |

- `IN_SCOPE` chiếm 86,51% dòng giao dịch và 74,41% giá trị bán.
- `OUT_OF_SCOPE` chiếm 1,41% dòng giao dịch và 8,61% giá trị bán.
- `REVIEW` chiếm 12,09% dòng giao dịch và 16,97% giá trị bán.

Có 17 mã sản phẩm giao dịch không tồn tại trong lookup. Sau khi bổ sung chúng, `product_scope.csv` có 92.348 mã, trong đó 34.692 mã thuộc `REVIEW`.

Số sản phẩm có giao dịch được đếm từ transactions, không đồng nhất với số sản phẩm trong lookup. Số giỏ hàng và hộ gia đình có thể chồng lặp giữa các trạng thái, nên không cộng trực tiếp để suy ra tổng nguồn.

## 5. Kiểm tra và đối soát

Kết quả lần chạy:

- Khóa sản phẩm trong lookup duy nhất và không thiếu.
- Phép nối giao dịch với kết quả phân loại là nhiều–một.
- Không tăng hoặc mất dòng giao dịch sau nối.
- Tổng số dòng của ba trạng thái bằng 1.469.307: `PASS`.
- Tổng giá trị bán của ba trạng thái bằng 4.596.039,58 USD: `PASS`.
- Đối soát tiền sử dụng số nguyên cent sau khi kiểm tra độ chính xác của nguồn.
- Mã SHA-256 của hai tệp đầu vào được lưu trong `validation.json`.

`PASS` xác nhận tính nhất quán của phép xử lý và đối soát, không chứng minh mọi sản phẩm đã được phân loại đúng về nghiệp vụ.

## 6. Cách chạy và kết quả đầu ra

Chạy từ thư mục gốc project:

```bash
python src/classify_fmcg.py --data data/raw/complete_journey --out data/landing/fmcg_classification_v1_3