# Invoice OCR (Nhận diện hóa đơn tiếng Việt)

Ứng dụng web đơn giản sử dụng AI để tự động trích xuất thông tin quan trọng từ hóa đơn tiếng Việt với độ chính xác cao.

## 🔍 Tính năng nổi bật

- 📸 Cho phép **tải ảnh hóa đơn** (định dạng JPG, PNG) và trích xuất thông tin dưới dạng cấu trúc
- 🤖 Pipeline OCR kết hợp:
  - `PaddleOCR` để phát hiện vùng chứa chữ trên ảnh
  - `VietOCR` (mô hình VGG Transformer) để nhận diện nội dung chữ viết chính xác
- 🧠 Xử lý ảnh thông minh:
  - Cắt vùng chữ đã phát hiện
  - Ghép các dòng văn bản
  - Chuẩn hóa dữ liệu đầu ra giúp tăng độ chính xác
- 📝 Tự động trích xuất các trường thông tin quan trọng:
  - Tên quán
  - Số điện thoại
  - Địa chỉ
  - Mã hóa đơn
  - Ngày hóa đơn
  - Thông tin món ăn
  - Tổng tiền
- 🧑‍💻 Giao diện cho phép chỉnh sửa kết quả trước khi lưu
- 🗄️ Lưu dữ liệu vào **cơ sở dữ liệu MySQL** qua Python connector
- 🌐 Giao diện web thân thiện, xây dựng bằng Streamlit

## 🛠️ Yêu cầu:
- Python 3.10.16
- torch (PyTorch)
- opencv-python
- pandas
- Pillow
- paddleocr
- vietocr
- streamlit
- mysql-connector-python

## 🖼️ Ảnh demo

![Ảnh demo](image/demo.png)  


## 🚀 Hướng dẫn chạy ứng dụng
  # 1. Clone repository
  
  ```bash
  git clone https://github.com/PakeNguyen/invoice_ocr_vietnamese.git
  cd invoice_ocr_vietnamese
  ```
  # 2. Chạy lệnh (streamlit run streamlit_app.py) trong terminal khi ở trong thư mục invoice_ocr_vietnamese
