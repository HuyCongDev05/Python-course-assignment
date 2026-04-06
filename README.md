# 🏢 Hệ thống Quản lý Ký túc xá (Dormitory Management System)

Ứng dụng quản lý ký túc xá hiện đại, chuyên nghiệp dành cho các trường đại học và cơ sở lưu trú. Được xây dựng trên nền tảng Python mạnh mẽ với giao diện người dùng trực quan, hệ thống giúp tối ưu hóa quy trình quản lý sinh viên, phòng ở, hợp đồng và thanh toán.

---

## ✨ Tính năng nổi bật

- **Quản lý Bảo mật & Phân quyền**:
  - Hệ thống đăng nhập an toàn với mật khẩu được mã hóa (hashing).
  - Phân quyền người dùng linh hoạt: **Quản trị viên (Admin)**, **Nhân viên (Staff)** và **Sinh viên (Student)**.
- **Quản lý Sinh viên**:
  - Lưu trữ hồ sơ chi tiết (Mã SV, họ tên, giới hạn, liên hệ, quê quán).
  - Tìm kiếm và lọc thông tin sinh viên thông minh.
- **Quản lý Phòng ở (Room Management)**:
  - Theo dõi trạng thái phòng thời gian thực (Còn trống, Đã đầy, Bảo trì).
  - Quản lý loại phòng, sức chứa và đơn giá thuê.
- **Quản lý Hợp đồng (Contract Management)**:
  - Quy trình lập hợp đồng thuê phòng giữa sinh viên và nhà trường.
  - Tự động theo dõi thời hạn hợp đồng (Hiệu lực, Hết hạn, Đã chấm dứt).
- **Quản lý Thanh toán (Payment Management)**:
  - Lập hóa đơn tiền phòng, điện, nước hàng tháng.
  - Ghi nhận và theo dõi lịch sử thanh toán của từng sinh viên.
- **Bảng điều khiển (Dashboard)**:
  - Tổng hợp số liệu thống kê nhanh về tình trạng phòng và số lượng sinh viên.

---

## 🛠 Công nghệ sử dụng

- **Ngôn ngữ**: Python 3.8+
- **Giao diện (UI)**: PyQt5 với phong cách thiết kế hiện đại (Custom QSS).
- **Cơ sở dữ liệu**: MySQL Server.
- **ORM**: SQLAlchemy (Giúp tương tác database an toàn, tối ưu hiệu suất).
- **Tiện ích**: `pymysql`, `python-dotenv`, `bcrypt`.

---

## 📁 Cấu trúc thư mục dự án

```text
├── config/             # Cấu hình kết nối MySQL & SQLAlchemy
├── models/             # Định nghĩa các bảng Database (ORM Models)
├── services/           # Xử lý logic nghiệp vụ xử lý dữ liệu
├── ui/                 # Giao diện người dùng
│   ├── resources/      # Các tệp tài nguyên, CSS (style.qss)
│   └── views/          # Mã nguồn các màn hình chức năng
├── utils/              # Các hàm tiện ích (Bảo mật, định dạng dữ liệu)
├── .env                # Cấu hình biến môi trường và thông tin kết nối DB
├── db_setup.py         # Script khởi tạo cơ sở dữ liệu ban đầu
├── main.py             # Điểm khởi chạy ứng dụng chính
├── requirements.txt    # Danh sách các thư viện cần cài đặt
└── README.md           # Tài liệu hướng dẫn dự án
```

---

## 🚀 Hướng dẫn cài đặt & Chạy ứng dụng

### 1. Chuẩn bị môi trường
- Cài đặt **Python 3.8** trở lên.
- Cài đặt **MySQL Server** và đảm bảo dịch vụ đang hoạt động.

### 2. Cài đặt thư viện
Mở Command Prompt hoặc Terminal tại thư mục dự án và thực hiện lệnh:
```bash
pip install -r requirements.txt
```

### 3. Cấu hình môi trường

Sao chép tệp cấu hình mẫu và điền thông tin kết nối MySQL của bạn:

```bash
cp .env.example .env
```

Mở tệp `.env` và cập nhật các thông số sau:
- `DB_HOST`: Địa chỉ Database (thường là `localhost`)
- `DB_USER`: Tên đăng nhập SQL (mặc định là `root`)
- `DB_PASSWORD`: Mật khẩu của bạn
- `DB_NAME`: `dorm_management`
- `DB_PORT`: `3306`

---

### 4. Khởi tạo dữ liệu
Chạy script sau để tự động tạo cơ sở dữ liệu và các bảng cần thiết:
```bash
python db_setup.py
```
*Sau khi hoàn tất, hệ thống sẽ tự động tạo tài khoản Quản trị viên mặc định:*
- **Tên đăng nhập**: `admin`
- **Mật khẩu**: `admin123`

### 5. Khởi chạy ứng dụng
Chạy tệp `main.py` để mở giao diện quản lý:
```bash
python main.py
```

---

## 📝 Lưu ý quan trọng
- Luôn đảm bảo MySQL Server đang chạy trước khi mở ứng dụng.
- Nếu gặp lỗi kết nối, hãy kiểm tra kỹ các thông số trong tệp `.env`.
- Mã nguồn này được bảo vệ bởi bản quyền nội bộ.

---
*Phát triển và duy trì bởi huycongdev05*
