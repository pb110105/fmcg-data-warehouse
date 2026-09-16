# Nguồn dữ liệu

## 1. Thông tin chung

- Tên bộ dữ liệu: **Breakfast at the Frat**.
- Nhà cung cấp: **dunnhumby**.
- Trang nguồn: <https://www.dunnhumby.com/source-files/>.
- Ngày kiểm tra nguồn: 15/09/2026.
- File dữ liệu: `dunnhumby - Breakfast at the Frat.xlsx`.
- Tài liệu đi kèm: `dunnhumby - Breakfast at the Frat User Guide.pdf`.
- Mục đích sử dụng: học tập và thực hiện tiểu luận chuyên ngành.

dunnhumby mô tả đây là bộ dữ liệu đại diện cho thông tin bán hàng và hỗ trợ khuyến mãi của các sản phẩm thuộc bốn ngành hàng trong 156 tuần. Nguồn cung cấp số lượng bán, lượt mua có sản phẩm, số hộ gia đình mua, doanh số, giá cơ sở, giá tại kệ, hình thức hỗ trợ khuyến mãi, thông tin sản phẩm và thông tin cửa hàng.

## 2. Phạm vi dữ liệu

Dữ liệu giao dịch bao phủ từ ngày 14/01/2009 đến ngày 04/01/2012, gồm 156 mốc tuần liên tục, cách nhau bảy ngày. Một bản ghi mô tả kết quả bán của một sản phẩm tại một cửa hàng trong một tuần.

Bộ dữ liệu gồm:

- 524.950 bản ghi bán hàng.
- 77 cửa hàng có phát sinh bán hàng.
- 55 sản phẩm có phát sinh bán hàng.
- 58 sản phẩm trong bảng tra cứu.
- Bốn bang: Indiana, Kentucky, Ohio và Texas.
- Ba phân khúc cửa hàng: `VALUE`, `MAINSTREAM` và `UPSCALE`.

## 3. Nguyên tắc quản lý dữ liệu nguồn

- File ZIP tải từ nguồn được giữ nguyên trong `data/raw`.
- File Excel được giải nén vào `data/landing` để pipeline đọc.
- User Guide được sử dụng làm tài liệu giải thích dữ liệu.
- Không chỉnh sửa trực tiếp file ZIP hoặc file Excel nguồn.

## 4. Giới hạn

- Dữ liệu được tổng hợp theo sản phẩm–cửa hàng–tuần, không chứa từng hóa đơn.
- Không có mã khách hàng hoặc thông tin khách hàng cá nhân.
- Không có giá vốn, chi phí khuyến mãi hoặc lợi nhuận.
- `VISITS` là số lượt mua có chứa một sản phẩm cụ thể; tổng `VISITS` giữa nhiều sản phẩm không phải số giỏ hàng duy nhất của cửa hàng.
- `HHS` là số hộ gia đình mua một sản phẩm trong một tuần; tổng `HHS` giữa các sản phẩm không phải số hộ gia đình duy nhất.
- Kết quả khuyến mãi chỉ được diễn giải dưới dạng mối liên hệ và chênh lệch quan sát được.
- Kết quả chỉ phản ánh các sản phẩm, cửa hàng và thời gian trong bộ dữ liệu, không đại diện cho toàn bộ thị trường FMCG hoặc thị trường Việt Nam.

## 5. Tài liệu nguồn

1. dunnhumby, “Source Files – Breakfast at the Frat,” truy cập ngày 15/09/2026, <https://www.dunnhumby.com/source-files/>.
2. dunnhumby, *Breakfast at the Frat: A Time Series Analysis – User Guide*, 2023.

