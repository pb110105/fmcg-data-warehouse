# Định nghĩa KPI

## 1. Quy ước chung

### 1.1. Phạm vi dữ liệu

* KPI bán hàng và giá sử dụng giao dịch thuộc phạm vi FMCG đã chốt.
* Sản phẩm chưa xác định phạm vi được báo cáo riêng, không tự động tính vào FMCG.
* KPI trưng bày/quảng cáo sử dụng các giao dịch trên và phân biệt trạng thái khớp hoặc không khớp thông tin hỗ trợ.
* KPI chiến dịch–coupon sử dụng toàn bộ bản ghi chiến dịch–coupon nguồn; chưa giới hạn theo sản phẩm thực tế được mua.
* Mọi tỷ lệ phải dùng tử số và mẫu số có phạm vi nhất quán.

### 1.2. Grain

| Tập dữ liệu phân tích       | Grain                                                       |
| --------------------------- | ----------------------------------------------------------- |
| Bán hàng                    | Sản phẩm trong một giỏ hàng                                 |
| So sánh trưng bày/quảng cáo | Sản phẩm–cửa hàng–tuần có phát sinh giao dịch thuộc phạm vi |
| Hộ nhận chiến dịch          | Chiến dịch–hộ gia đình                                      |
| Sử dụng coupon              | Hộ–coupon–chiến dịch–ngày sử dụng theo bản ghi nguồn        |

Không nối trực tiếp các Fact rồi cộng số đo nếu phép nối tạo quan hệ nhiều–nhiều.

### 1.3. Quy tắc tính

* Công thức tỷ lệ dưới đây trả về giá trị từ 0 đến 1, trừ các chỉ số biến động có thể âm hoặc vượt 1. Định dạng phần trăm ở lớp hiển thị.
* Dùng `NULLIF(mẫu_số, 0)` khi chia.
* Mẫu số bằng 0 trả về NULL và hiển thị “Không đủ điều kiện tính”.
* Không thay NULL bằng 0 một cách mặc định.
* Giá trị tiền sử dụng USD theo định nghĩa nguồn.
* Không làm tròn từng dòng trước khi tổng hợp; chỉ làm tròn ở bước hiển thị.

## 2. Các trường phục vụ tính toán

### 2.1. Cờ có khoản giảm giá

Một dòng có giảm giá nếu ít nhất một trường sau lớn hơn 0:

* `retail_disc`
* `coupon_disc`
* `coupon_match_disc`

Quy ước trường dẫn xuất:

`discount_any = 1` nếu có ít nhất một khoản giảm giá; ngược lại bằng 0.

Cờ này chỉ mô tả khoản giảm giá ghi trong giao dịch. Nó không thay thế trạng thái trưng bày/quảng cáo.

### 2.2. Trạng thái trưng bày và quảng cáo

Trước khi nối với giao dịch, tổng hợp `promotions` thành đúng
một dòng trên mỗi `product_id + store_id + week`.

Giữ mã nguồn dưới dạng chuỗi và phân loại theo bảng sau:

| Trường | Nhóm mã | Ý nghĩa phân loại |
|---|---|---|
| `display_location` | `0`, `A` | Không trưng bày đặc biệt |
| `display_location` | `1`, `2`, `3`, `4`, `5`, `6`, `7`, `9` | Có trưng bày |
| `mailer_location` | `0` | Không quảng cáo qua mailer |
| `mailer_location` | `A`, `C`, `D`, `F`, `H`, `J`, `L`, `P`, `X`, `Z` | Có quảng cáo qua mailer |
| Cả hai trường | NULL, chuỗi rỗng hoặc mã ngoài danh sách tương ứng | Chưa xác định; gắn cờ kiểm tra |

Mã `A` có ý nghĩa khác nhau giữa hai trường.
Không dùng điều kiện `khác "0"` để xác định có trưng bày.

#### Quy tắc tổng hợp cờ

Áp dụng riêng cho `has_display` và `has_mailer`
trong từng tổ hợp sản phẩm–cửa hàng–tuần:

- TRUE: có ít nhất một mã hợp lệ thuộc nhóm có hỗ trợ.
- FALSE: tất cả mã đều hợp lệ và thuộc nhóm không hỗ trợ.
- NULL: không có mã xác nhận có hỗ trợ, đồng thời có mã
  thiếu hoặc chưa nhận diện.

Đặt `promotion_code_unknown_flag = TRUE` nếu một trong hai
trường có mã thiếu hoặc chưa nhận diện, kể cả khi đã xác định
được cờ TRUE từ bản ghi khác trong cùng tổ hợp.

Giữ tập mã nguồn và số dòng nguồn sau tổng hợp để truy vết.

#### Phân loại trạng thái phục vụ KPI

| `support_status` | Điều kiện |
|---|---|
| `NO_DISPLAY_MAILER` | Có bản ghi khớp, không có mã chưa biết và hai cờ đều FALSE |
| `DISPLAY_ONLY` | Có bản ghi khớp, không có mã chưa biết; has_display = TRUE và has_mailer = FALSE |
| `MAILER_ONLY` | Có bản ghi khớp, không có mã chưa biết; has_display = FALSE và has_mailer = TRUE |
| `DISPLAY_MAILER` | Có bản ghi khớp, không có mã chưa biết và hai cờ đều TRUE |
| `UNKNOWN` | Không có bản ghi khớp, có mã chưa biết hoặc có cờ NULL |

Các dòng UNKNOWN được báo cáo riêng và không tham gia
so sánh giữa bốn trạng thái hỗ trợ đã xác định.

Phân biệt hai trường hợp:
- Không tìm thấy bản ghi khuyến mãi tương ứng.
- Có bản ghi khớp nhưng chưa phân loại được đầy đủ.

Cả hai có thể hiển thị UNKNOWN, nhưng phải giữ nguyên lý do
để tính KPI bao phủ và kiểm tra chất lượng.

NO_DISPLAY_MAILER chỉ có nghĩa không ghi nhận trưng bày
đặc biệt hoặc quảng cáo qua mailer; giao dịch vẫn có thể
có giảm giá hoặc coupon.

### 2.3. Tập hợp lệ để phân tích giá đơn vị

KPI giá đơn vị sử dụng các dòng:

* Thuộc phạm vi sản phẩm đã xác định.
* Có `quantity > 0`.
* Có `sales_value` hợp lệ.
* Có đơn vị số lượng phù hợp với cách so sánh.

Ưu tiên phân tích cùng một sản phẩm qua thời gian hoặc cửa hàng. Không gọi giá trị bình quân trên nhiều sản phẩm khác quy cách là giá của một sản phẩm điển hình.

## 3. KPI doanh số và sản lượng

| Mã      | KPI                                          | Công thức                                                                         | Đơn vị       | Điều kiện và diễn giải                                                      |
| ------- | -------------------------------------------- | --------------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------- |
| KPI-S01 | Tổng giá trị bán                             | `SUM(sales_value)`                                                                | USD          | Giá trị nhà bán lẻ nhận được từ giao dịch thuộc phạm vi                     |
| KPI-S02 | Tổng số lượng nguồn                          | `SUM(quantity)`                                                                   | Đơn vị nguồn | Chỉ diễn giải là sản lượng tổng hợp khi các đơn vị có thể cộng              |
| KPI-S03 | Số giỏ hàng có mua trong phạm vi             | `COUNT(DISTINCT basket_id)`                                                       | Giỏ hàng     | Một giỏ được tính một lần trong phạm vi lọc                                 |
| KPI-S04 | Số hộ có mua trong phạm vi                   | `COUNT(DISTINCT household_id)`                                                    | Hộ           | Không phải số cá nhân                                                       |
| KPI-S05 | Giá trị bán trong phạm vi bình quân trên giỏ | `SUM(sales_value) / NULLIF(COUNT(DISTINCT basket_id), 0)`                         | USD/giỏ      | Chỉ tính phần hàng thuộc phạm vi; không gọi là giá trị toàn bộ giỏ          |
| KPI-S06 | Tỷ trọng giá trị bán của nhóm                | Giá trị bán của nhóm / giá trị bán toàn bộ phạm vi so sánh                        | Tỷ lệ        | Giữ bộ lọc thời gian và phạm vi; chỉ bỏ bộ lọc nhóm cần tính tỷ trọng ở mẫu |
| KPI-S07 | Biến động giá trị bán theo tháng             | `(Giá trị tháng hiện tại - Giá trị tháng trước) / NULLIF(Giá trị tháng trước, 0)` | Tỷ lệ        | Chỉ so sánh tháng có phạm vi ngày quan sát tương đương                      |

Không cộng số giỏ hàng hoặc số hộ đã đếm riêng theo sản phẩm để suy ra số phân biệt toàn bộ.

KPI theo ngày, tháng, quý và năm sử dụng ngày giao dịch
theo múi giờ America/New_York.

Khoảng ngày giao dịch là 01/01/2017–31/12/2017.
Không tạo tháng bán hàng 01/2018 từ cách hiển thị timestamp theo UTC.

KPI theo tuần sử dụng week nguồn, đã được đối chiếu khớp
với quy tắc `%W + 1` trên ngày giao dịch theo America/New_York.

Tuần 1 chỉ có một ngày thuộc phạm vi dữ liệu, vì vậy không so sánh
trực tiếp tổng doanh số tuần này với tuần có đủ bảy ngày quan sát.

Ngày 25/12/2017 vẫn có trong Dim_Date và thuộc tuần 53,
dù không có giao dịch nguồn. Khi tính bình quân theo ngày,
phải nêu rõ mẫu số là số ngày lịch hay số ngày có giao dịch.

## 4. KPI giá và các khoản giảm giá

| Mã      | KPI                                        | Công thức                                                              | Đơn vị           | Điều kiện và diễn giải                                     |
| ------- | ------------------------------------------ | ---------------------------------------------------------------------- | ---------------- | ---------------------------------------------------------- |
| KPI-P01 | Giá trị bán bình quân trên một đơn vị      | `SUM(sales_value) / NULLIF(SUM(quantity), 0)` trên tập hợp lệ về giá   | USD/đơn vị nguồn | Không mặc định là giá khách thực trả hoặc giá niêm yết     |
| KPI-P02 | Tổng giảm giá bán lẻ                       | `SUM(retail_disc)`                                                     | USD              | Khoản giảm từ nhà bán lẻ được ghi nhận trên dòng giao dịch |
| KPI-P03 | Tổng giảm giá coupon nhà sản xuất          | `SUM(coupon_disc)`                                                     | USD              | Báo cáo riêng với giảm giá nhà bán lẻ                      |
| KPI-P04 | Tổng giảm giá đối ứng coupon               | `SUM(coupon_match_disc)`                                               | USD              | Phần nhà bán lẻ hỗ trợ thêm theo coupon                    |
| KPI-P05 | Tỷ lệ dòng mua có giảm giá                 | Số dòng có `discount_any = 1` / tổng số dòng trong phạm vi             | Tỷ lệ            | Không phải tỷ lệ giỏ hàng hoặc tỷ lệ giảm giá tiền         |
| KPI-P06 | Tỷ trọng giá trị bán trên dòng có giảm giá | Tổng `sales_value` của dòng có `discount_any = 1` / tổng `sales_value` | Tỷ lệ            | Không phải tỷ lệ tiền được giảm                            |

### Các chỉ số chưa chốt

Chưa đưa vào bộ KPI chính thức:

* Giá niêm yết hoặc giá trước giảm.
* Tiền khách hàng thực trả.
* Tỷ lệ giảm giá so với giá trước giảm.
* Tổng mức giảm kết hợp cả ba trường nếu chưa xác minh quan hệ giữa chúng.

Các công thức này cần được đối chiếu ý nghĩa trường và quy ước dấu, đặc biệt với 3.507 dòng có `coupon_disc > sales_value`.

Không sử dụng lại công thức dựa trên `BASE_PRICE` của bộ dữ liệu cũ.

## 5. KPI trưng bày và quảng cáo

### 5.1. Kiểm tra mức bao phủ

Tính sau khi nối giao dịch với bảng khuyến mãi đã tổng hợp về grain duy nhất.

| Mã      | KPI                                            | Công thức                                                                | Đơn vị |
| ------- | ---------------------------------------------- | ------------------------------------------------------------------------ | ------ |
| KPI-M01 | Tỷ lệ dòng giao dịch khớp thông tin khuyến mãi | Số dòng giao dịch có bản ghi khớp / tổng số dòng giao dịch trong phạm vi | Tỷ lệ  |
| KPI-M02 | Tỷ trọng giá trị bán khớp thông tin khuyến mãi | Tổng `sales_value` của dòng khớp / tổng `sales_value` trong phạm vi      | Tỷ lệ  |

Nếu bản ghi khớp nhưng mã phân loại không hợp lệ, vẫn phân biệt tình trạng khớp với tình trạng phân loại hợp lệ. Các dòng này chưa tham gia so sánh trạng thái.

### 5.2. So sánh theo trạng thái

Tạo tập tổng hợp bán hàng theo sản phẩm–cửa hàng–tuần:

* `weekly_sales_value`: tổng `sales_value`.
* `weekly_quantity`: tổng `quantity`.
* `support_status`: trạng thái hỗ trợ tương ứng.

Tập này chỉ gồm các tổ hợp có phát sinh giao dịch thuộc phạm vi. Không tự tạo doanh số bằng 0 cho các tổ hợp không có giao dịch vì chưa biết sản phẩm có được bán tại cửa hàng trong tuần đó hay không.

| Mã      | KPI                                                | Công thức                                                                                              | Đơn vị              | Điều kiện                                                            |
| ------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------- | -------------------------------------------------------------------- |
| KPI-M03 | Tỷ trọng giá trị bán theo trạng thái               | Giá trị bán của trạng thái / tổng giá trị bán của các trạng thái đã xác định                           | Tỷ lệ               | Loại `UNKNOWN` khỏi cả phạm vi so sánh; công bố mức bao phủ kèm theo |
| KPI-M04 | Giá trị bán bình quân trên tổ hợp có phát sinh mua | `SUM(weekly_sales_value) / COUNT(*)` theo trạng thái                                                   | USD/tổ hợp          | Mỗi dòng là một sản phẩm–cửa hàng–tuần                               |
| KPI-M05 | Số lượng bình quân trên tổ hợp có phát sinh mua    | `SUM(weekly_quantity) / COUNT(*)` theo trạng thái                                                      | Đơn vị nguồn/tổ hợp | Chỉ so sánh trong phạm vi đơn vị phù hợp                             |
| KPI-M06 | Chênh lệch giá trị bán bình quân quan sát          | `AVG(weekly_sales_value có hỗ trợ) / NULLIF(AVG(weekly_sales_value không trưng bày/quảng cáo), 0) - 1` | Tỷ lệ               | Tính trong cùng cặp sản phẩm–cửa hàng, có cả hai nhóm tuần           |

Trong KPI-M06:

* “Có hỗ trợ” gồm `DISPLAY_ONLY`, `MAILER_ONLY`, `DISPLAY_MAILER`.
* Nhóm đối chiếu là `NO_DISPLAY_MAILER`.
* Không sử dụng `UNKNOWN`.
* Hai nhóm đều là các tuần có phát sinh giao dịch.
* Không gọi kết quả là causal uplift hoặc phần doanh số do khuyến mãi tạo ra.
* Chưa gộp các tỷ lệ của nhiều cặp sản phẩm–cửa hàng thành một tỷ lệ chung nếu chưa quy định trọng số.

Mọi biểu đồ so sánh phải hiển thị số tổ hợp quan sát của từng nhóm để tránh diễn giải chênh lệch do quy mô mẫu.

## 6. KPI chiến dịch và coupon

### 6.1. Phạm vi

Tính ở cấp từng chiến dịch, sử dụng:

* `campaigns` để xác định hộ nhận chiến dịch.
* `campaign_descriptions` để bổ sung thời gian và loại chiến dịch.
* `coupon_redemptions` để đếm bản ghi sử dụng coupon.

KPI được tính trên toàn bộ chiến dịch–coupon nguồn. Không tự gắn nhãn “chỉ FMCG” vì chưa xác định được sản phẩm thực tế của từng bản ghi sử dụng coupon.

### 6.2. Định nghĩa

| Mã      | KPI                                          | Công thức theo từng chiến dịch                            | Đơn vị     | Lưu ý                                                      |
| ------- | -------------------------------------------- | --------------------------------------------------------- | ---------- | ---------------------------------------------------------- |
| KPI-C01 | Số hộ nhận chiến dịch                        | `COUNT(DISTINCT household_id)` trong `campaigns`          | Hộ         | Đếm cặp hộ–chiến dịch hợp lệ                               |
| KPI-C02 | Số hộ có sử dụng coupon                      | `COUNT(DISTINCT household_id)` trong `coupon_redemptions` | Hộ         | Đối chiếu hộ thuộc chiến dịch                              |
| KPI-C03 | Số bản ghi sử dụng coupon                    | `COUNT(*)` trên tập sử dụng hợp lệ                        | Bản ghi    | Không đếm trên kết quả nối với danh sách sản phẩm áp dụng  |
| KPI-C04 | Tỷ lệ hộ sử dụng coupon                      | `KPI-C02 / NULLIF(KPI-C01, 0)`                            | Tỷ lệ      | Không phải tỷ lệ coupon đã dùng trên tổng coupon phát hành |
| KPI-C05 | Bản ghi sử dụng bình quân trên hộ có sử dụng | `KPI-C03 / NULLIF(KPI-C02, 0)`                            | Bản ghi/hộ | Mẫu số chỉ gồm hộ có sử dụng                               |
| KPI-C06 | Số mã coupon được sử dụng                    | `COUNT(DISTINCT coupon_upc)` trong từng chiến dịch        | Mã coupon  | Không phải số sản phẩm đã mua                              |

“Tập sử dụng hợp lệ” gồm các bản ghi:

* Khớp cặp hộ–chiến dịch trong `campaigns`.
* Khớp cặp coupon–chiến dịch trong danh mục coupon.
* Có ngày sử dụng thuộc thời gian chiến dịch.
* Đã áp dụng quy tắc xử lý trùng được công bố.

Kiểm tra tồn tại coupon phải dùng tập cặp coupon–chiến dịch phân biệt, tránh nhân dòng bởi nhiều sản phẩm áp dụng.

Khi tổng hợp nhiều chiến dịch, phải phân biệt:

* Số hộ duy nhất trên toàn bộ chiến dịch.
* Số lượt hộ–chiến dịch.

Không cộng số hộ từng chiến dịch rồi gọi là số hộ duy nhất.

### 6.3. Giới hạn

Chưa tính:

* Doanh số trực tiếp do chiến dịch tạo ra.
* Doanh số trực tiếp do từng coupon tạo ra.
* ROI chiến dịch.
* Tỷ lệ coupon sử dụng trên tổng coupon phát hành khi chưa biết đầy đủ mẫu số phát hành.

## 7. Quy tắc thời gian

* KPI theo ngày, tháng, quý sử dụng ngày giao dịch sau khi xác minh cách xử lý múi giờ.
* KPI trưng bày/quảng cáo sử dụng mã tuần nguồn đã được ánh xạ nhất quán.
* Không thay `week` nguồn bằng tuần ISO nếu chưa đối chiếu.
* KPI sử dụng coupon dùng `redemption_date`.
* KPI-C04 toàn chiến dịch dùng toàn bộ thời gian quan sát của chiến dịch.
* Nếu lọc sử dụng coupon theo một khoảng ngày, phải ghi rõ đây là tỷ lệ trong khoảng quan sát, không phải kết quả toàn chiến dịch.
* Chiến dịch bắt đầu trước hoặc kết thúc sau khoảng dữ liệu sử dụng coupon phải được đánh dấu chưa quan sát đầy đủ; không xếp hạng ngang với chiến dịch được quan sát trọn vẹn mà không giải thích.

## 8. Điều kiện kiểm tra trước khi công bố

* Tổng giá trị bán khớp kết quả đối soát ETL theo phạm vi.
* Phép nối khuyến mãi không làm tăng số dòng giao dịch hoặc tổng tiền.
* Giỏ hàng và hộ được đếm phân biệt ở đúng phạm vi.
* KPI giá loại số lượng bằng 0 khỏi cả tử số và mẫu số.
* Các trạng thái chưa biết được trình bày riêng.
* KPI sử dụng coupon không bị nhân theo số sản phẩm áp dụng.
* Dashboard ghi rõ phạm vi FMCG của bán hàng và phạm vi toàn nguồn của chiến dịch–coupon.
* Chênh lệch khuyến mãi được diễn giải là quan sát, không phải quan hệ nhân quả.


## Bổ sung: Quy tắc KPI số lượng, doanh số và giảm giá

### 1. Phạm vi áp dụng

- Chỉ sử dụng giao dịch có `scope_status = 'IN_SCOPE'`.
- Phiên bản phân loại hiện tại: `1.3-cosmetics-and-exclusions`.
- Tiền tệ: USD.
- Số lượng: đơn vị ghi nhận trong dữ liệu nguồn.
- Các công thức dưới đây dùng tên cột nguồn; tên cột đích sẽ được
  ánh xạ trong giai đoạn thiết kế.
- Điều kiện lọc KPI không đồng nghĩa với xóa bản ghi khỏi kho dữ liệu.

### 2. KPI được chốt

| KPI | Công thức | Điều kiện và cách diễn giải |
|---|---|---|
| Doanh số FMCG | `SUM(sales_value)` | Tổng giá trị nhà bán lẻ nhận theo nguồn; không trừ thêm các khoản giảm giá; giữ cả dòng có số lượng bằng 0 |
| Số lượng theo sản phẩm | `SUM(quantity)` | Tổng đơn vị nguồn; ưu tiên phân tích theo cùng sản phẩm; không gọi là kg, lít hoặc gói khi chưa xác minh đơn vị |
| Giá trị bán bình quân trên đơn vị nguồn | `SUM(sales_value) / NULLIF(SUM(quantity), 0)` | Cùng tập dòng có `quantity > 0` và `sales_value >= 0`; cả hai trường phải hợp lệ; ưu tiên tính theo sản phẩm |
| Giảm giá thẻ khách hàng ghi nhận | `SUM(retail_disc)` | Tổng khoản giảm giá thẻ theo nguồn |
| Giảm giá coupon nhà sản xuất ghi nhận | `SUM(coupon_disc)` | Tổng khoản giảm từ coupon nhà sản xuất theo nguồn |
| Giảm giá đối ứng coupon ghi nhận | `SUM(coupon_match_disc)` | Tổng khoản giảm đối ứng coupon theo nguồn |

Các tổng tiền sử dụng giá trị nguồn hợp lệ, hữu hạn và không âm.
Dữ liệu hiện tại của `IN_SCOPE` không có giá trị thiếu, vô hạn hoặc âm
trong các trường này. Nếu xuất hiện ở lần nạp sau, phải ghi nhận lỗi
và công bố số dòng không được tính; không tự thay bằng 0.

### 3. Điều kiện tính giá trị bán bình quân

Tập dòng hợp lệ:

```sql
WHERE scope_status = 'IN_SCOPE'
  AND quantity IS NOT NULL
  AND quantity > 0
  AND sales_value IS NOT NULL
  AND sales_value >= 0