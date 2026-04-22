# Tài liệu Kỹ thuật Dự án Quản lý Ký túc xá

Tài liệu này trình bày chi tiết về kiến trúc, các công nghệ áp dụng, quy trình xử lý dữ liệu và các kỹ thuật tối ưu hóa
trong hệ thống Quản lý Ký túc xá (Dormitory Management System).

---

## 1. Kiến trúc Hệ thống (Architecture)

Dự án được xây dựng theo mô hình **Service-Repository** (một biến thể của MVC), giúp tách biệt rõ ràng giữa giao diện
người dùng và logic nghiệp vụ.

- **Lớp Giao diện (UI Layer)**: Nằm trong thư mục `ui/`, sử dụng thư viện **PyQt5**. Bao gồm các `Views` (trang chính)
  và `Widgets` (các thành phần tùy chỉnh).
- **Lớp Dịch vụ (Service Layer)**: Nằm trong thư mục `services/`, chứa logic nghiệp vụ chính như tính toán tiền phòng,
  xử lý đăng ký, đồng bộ trạng thái.
- **Lớp Mô hình (Model Layer)**: Nằm trong thư mục `models/`, định nghĩa cấu trúc cơ sở dữ liệu thông qua **SQLAlchemy
  ORM**.
- **Lớp Cấu hình & Tiện ích (Config & Utils)**: Quản lý kết nối cơ sở dữ liệu và các hàm bổ trợ (bảo mật, định dạng).

---

## 2. Mô hình hóa Dữ liệu (ORM Modeling)

Hệ thống sử dụng **SQLAlchemy** để ánh xạ các đối tượng Python tới cơ sở dữ liệu quan hệ (SQLite).

### Các thực thể chính:

- **User**: Quản lý tài khoản (Admin/Student), tên đăng nhập và mật khẩu băm.
- **Student**: Thông tin cá nhân sinh viên, liên kết với một `User` và một `Room`.
- **Room**: Thông tin phòng ở, sức chứa, đơn giá và trạng thái (Available, Occupied, Maintenance).
- **Contract**: Hợp đồng giữa sinh viên và phòng, quản lý ngày bắt đầu/kết thúc và tổng giá trị.
- **Payment**: Các khoản thanh toán liên quan đến hợp đồng (Tiền phòng, điện, nước).

> [!IMPORTANT]
> **Quan hệ dữ liệu**: Hệ thống quản lý chặt chẽ các quan hệ `1-n` giữa `Room -> Students` và `Contract -> Payments`,
> đảm bảo tính toàn vẹn dữ liệu khi xóa hoặc cập nhật.

---

## 3. Các Kỹ thuật Xử lý Dữ liệu Đặc biệt

### 3.1. Tự động hóa trạng thái (Automation Syncing)

Hệ thống tích hợp các hàm "tự phục hồi" và "tự cập nhật" trạng thái:

- **`refresh_contract_statuses`**: Tự động chuyển hợp đồng sang trạng thái `expired` khi quá ngày kết thúc và giải phóng
  chỗ trong phòng.
- **`_sync_room_status`**: Tự động tính toán lại trạng thái phòng dựa trên `current_occupancy` so với `capacity`.

### 3.2. Tính toán Logic Tài chính

- **Cơ chế tính phí tạm tính**: Hệ thống tự động tính tổng tiền hợp đồng dựa trên đơn giá phòng và số tháng lưu trú (
  được làm tròn theo quy tắc nội bộ).

---

## 4. Công nghệ Giao diện & UX (UI/UX Engineering)

Hệ thống được thiết kế với phong cách hiện đại, sử dụng các kỹ thuật cao cấp trong PyQt5:

### 4.1. Thiết kế Giao diện (QSS Styling)

- Toàn bộ giao diện được điều khiển bởi tệp `style.qss`, áp dụng các kỹ thuật:
    - **Gradients & Chủ đề màu**: Sử dụng hệ màu hài hòa (Amber, Green, Blue, Rose) cho các thẻ chỉ số (Metric Cards).
    - **Bo góc (Border Radius)**: Áp dụng bo góc cho hầu hết các frame và bảng để tạo cảm giác mềm mại.

### 4.2. Widget tùy chỉnh chuyên sâu

- **HoverTableWidget**: Widget bảng hỗ trợ hiệu ứng di chuột (hover color) và highlight dòng đang chọn bằng mã màu được
  tính toán động trong code.
- **SearchableComboBox**: Một component phức tạp kết hợp `QFrame` không viền và `QListWidget` để tạo ra hộp chọn có chức
  năng tìm kiếm thời gian thực (Real-time Filtering).

---

## 5. Cơ chế Bảo mật & Duy trì Phiên

### 5.1. Băm mật khẩu (Password Hashing)

Hệ thống không lưu trữ mật khẩu thuần túy. Thay vào đó, nó sử dụng:

- **Thuật toán**: PBKDF2 với SHA-256.
- **Salt**: 16 byte ngẫu nhiên cho mỗi mật khẩu.
- **Vòng lặp (Iterations)**: 260,000 vòng để đảm bảo khả năng chống tấn công brute-force.

### 5.2. Quản lý Phiên (Session Management)

- Thông tin người dùng được duy trì qua tệp `session.json` được mã hóa đơn giản để tự động đăng nhập trong lần khởi chạy
  tiếp theo.

---

## 6. Xử lý Lỗi & Validations

- Sử dụng cơ chế `commit/rollback` của SQLAlchemy để đảm bảo an toàn giao dịch.
- Kiểm tra dữ liệu đầu vào bằng `Regex` (đối với tên đăng nhập) và các hàm `validate` chuyên biệt trong từng hộp thoại (
  `Dialog`).
