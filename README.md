# Talkshow Person Video Trimmer 🎬

Ứng dụng desktop viết bằng Python (PySide6) tích hợp AI tự động phân tích nhiều video đầu vào, phát hiện và gom nhóm khuôn mặt của từng người xuất hiện (Joint Face Clustering), sau đó hỗ trợ cắt và xuất các phân đoạn video chỉ có người được chọn xuất hiện với độ chính xác từng khung hình (frame-accurate).

---

## ✨ Tính năng nổi bật

1. **Nhận diện & Gom nhóm khuôn mặt toàn cục (Joint Face Clustering)**:
   - Sử dụng mô hình **YuNet** để phát hiện khuôn mặt cực nhanh trên CPU.
   - Trích xuất đặc trưng khuôn mặt bằng mô hình **SFace** chạy trên GPU (CUDA) thông qua ONNX Runtime.
   - Gom nhóm khuôn mặt của cùng một người xuất hiện ở **nhiều video khác nhau** vào cùng một thẻ hiển thị duy nhất trong thư viện (Face Gallery).

2. **Quản lý hàng đợi quét song song (Parallel Scan Queue)**:
   - Hỗ trợ tải nhiều video cùng lúc bằng nút bấm hoặc kéo thả (Drag & Drop).
   - Kiểm soát chạy tối đa **2 tác vụ quét đồng thời** để tránh quá tải VRAM GPU. Các video còn lại tự động xếp hàng đợi (`[Đang chờ...]`) và tự kích hoạt khi có luồng trống.

3. **Cắt video chính xác tuyệt đối (Frame-Accurate Output Seeking)**:
   - Sử dụng cơ chế tìm kiếm đầu ra (Output Seeking) của FFmpeg kết hợp căn chỉnh khoảng thời gian (centered intervals), giúp loại bỏ hoàn toàn lỗi lệch/lẹm frame của người khác ở ranh giới cắt.

4. **Tùy chọn chế độ xuất linh hoạt**:
   - **Xuất riêng rẽ**: Cắt riêng và lưu thành các tệp video đã trim cạnh tệp gốc.
   - **Xuất gộp**: Tự động ghép nối tất cả phân đoạn của người được chọn từ mọi video đã quét thành một file video tổng hợp duy nhất.

5. **Giao diện chia đôi hiện đại (Side-by-Side QSS Premium)**:
   - Giao diện tối (Dark Mode) cao cấp với hiệu ứng ánh sáng neon cyan.
   - Cột bên trái hiển thị danh sách video, thanh tiến độ và thông số cài đặt. Cột bên phải hiển thị thư viện ảnh thẻ và các tùy chọn xuất video. Tên file hiển thị tự động rút gọn thông minh, chống lệch/giật giao diện khi log cập nhật.

---

## 🛠️ Yêu cầu hệ thống

- **Hệ điều hành**: Windows 10 / 11 (64-bit).
- **Python**: Phiên bản 3.12 (đã được cấu hình trong biến môi trường PATH).
- **GPU (Tùy chọn)**: Card đồ họa NVIDIA (ví dụ: RTX 3060) cùng driver CUDA mới nhất để tăng tốc độ trích xuất khuôn mặt bằng GPU.

---

## 🚀 Hướng dẫn cài đặt & Chạy ứng dụng (Tự động 100%)

Dự án đã được tối ưu hóa tự động hóa hoàn toàn. Bạn **không cần cài đặt thủ công** bất kỳ thư viện hay phần mềm bổ sung nào (kể cả FFmpeg hay các tệp mô hình AI).

1. Tải hoặc clone thư mục dự án này về máy tính.
2. Click đúp vào file **`run.bat`** ở thư mục gốc.

**Script `run.bat` sẽ tự động thực hiện:**
* Kiểm tra sự tồn tại của Python.
* Tự động khởi tạo môi trường ảo Python (`.venv/`) nếu chưa có.
* Kiểm tra hệ thống đã cài FFmpeg chưa. Nếu chưa, script sẽ **tự động tải gói FFmpeg Essentials** (khoảng 90MB), giải nén cục bộ và cài vào thư mục `.venv\Scripts\` (không làm ảnh hưởng đến biến môi trường hệ thống của bạn).
* Tự động tải/nâng cấp các thư viện Python cần thiết (`PySide6`, `opencv-python`, `numpy`, `onnxruntime-gpu`) từ `requirements.txt`.
* Tự động tải các file mô hình AI (`face_detection_yunet_2023mar.onnx` và `face_recognition_sface_2021dec.onnx`) từ OpenCV Zoo ngay lần đầu chạy ứng dụng.
* Khởi chạy ứng dụng desktop.

---

## 📂 Cấu trúc mã nguồn

- `main.py`: Điểm khởi chạy chính của ứng dụng, quản lý hàng đợi luồng, gom nhóm khuôn mặt toàn cục và các tương tác giao diện.
- `ui.py`: Định nghĩa giao diện, phong cách stylesheet (QSS Premium Dark) và thành phần `FaceCard`.
- `worker.py`: Các tiến trình chạy ngầm (`QThread`) để quét khuôn mặt và xuất video mà không gây đơ giao diện chính.
- `face_engine.py`: Tải và quản lý việc chạy mô hình YuNet/SFace (ONNX Runtime GPU / CPU).
- `video_utils.py`: Thuật toán chuyển đổi danh sách mốc thời gian sang phân đoạn và các lệnh FFmpeg cắt ghép video.
- `requirements.txt`: Danh sách các thư viện Python đi kèm phiên bản cố định.
- `run.bat`: Script khởi chạy tự động cài đặt mọi thành phần thiếu hụt.
- `.gitignore`: Cấu hình Git để loại trừ các tệp tạm, môi trường ảo nặng và video cục bộ.
