# Hướng dẫn chi tiết Logic AI Chatbot (DormChatService)

Tính năng Chatbot AI trong Hệ thống quản lý Ký túc xá (DormManager) sử dụng `DormChatService` để giao tiếp trực tiếp với người dùng và tư vấn, trả lời các thông tin liên quan tới phòng ở, hóa đơn, công nợ... 

Điểm nổi bật của kiến trúc này là sử dụng **Mô hình cung cấp ngữ cảnh động (Dynamic Context Injection)**. Dưới đây là phân tích chi tiết về logic hoạt động của AI Chatbot.

---

## 1. Luồng hoạt động chính (Workflow)

Khi người dùng gửi một câu hỏi từ giao diện (UI), quá trình xử lý trải qua các bước sau:

1. **Nhận câu hỏi**: Chatbot nhận `user_id` hiện tại và chuỗi `question` từ UI.
2. **Trích xuất Context (Ngữ cảnh)**: Dựa vào `user_id`, hệ thống truy vấn cơ sở dữ liệu (SQLite/MySQL) để lấy thông tin hồ sơ của tài khoản đang đăng nhập, danh sách phòng, hợp đồng và hóa đơn (nếu có).
3. **Xây dựng Prompt (System Prompt)**: Tạo ra một bộ quy tắc nghiêm ngặt kết hợp với dữ liệu ngữ cảnh (được format dưới dạng JSON) để gửi lên mô hình ngôn ngữ lớn (Gemini).
4. **Gọi API LLM (Gemini API)**: Đóng gói System Prompt và câu hỏi của người dùng thành payload chuẩn, sau đó gửi request thông qua HTTP tới Google AI Studio.
5. **Xử lý và Trả kết quả**: Phân tích cú pháp JSON trả về từ API, bóc tách câu trả lời của mô hình và trả ngược lại cho giao diện người dùng.

---

## 2. Kiến trúc Ngữ cảnh Động (Dynamic Context Injection)

LLM (Large Language Model) mặc định không biết gì về cơ sở dữ liệu của bạn. Để AI có thể trả lời chính xác "Tôi đang nợ bao nhiêu tiền?" hay "Còn phòng nào trống không?", chúng ta dùng kỹ thuật nhúng dữ liệu thật vào *System Instruction*.

### Hàm `_load_context(self, user_id)`

Hàm này nhận đầu vào là `user_id` và tiến hành các truy vấn (query) để xây dựng bộ từ điển ngữ cảnh (Context Dictionary):

- **Thông tin cơ bản**:
  - `access_scope`: Xác định phạm vi quyền truy cập. Nếu tài khoản có liên kết với một hồ sơ sinh viên, phạm vi là `student_self_only`. Nếu không, chỉ là `general_info_only` (chỉ xem thông tin phòng ở công cộng).
  - `current_account`: Lưu trữ ID, username và role của người dùng hiện tại.
  - `room_summary`: Tóm tắt toàn bộ danh sách phòng hiện tại trong KTX (bao nhiêu phòng trống, sức chứa, giá tiền).

- **Dữ liệu Cá nhân (Personal Data - Nếu có hồ sơ sinh viên)**:
  - Nếu `user_id` có map với bảng `Student`, hệ thống sẽ load thêm:
    - **`student_profile`**: Thông tin cá nhân (họ tên, email, sđt) và phòng đang ở.
    - **`contracts`**: Lịch sử các hợp đồng lưu trú (chỉ của sinh viên này).
    - **`payments`**: Toàn bộ các phiếu thanh toán liên quan đến sinh viên này (đã thu, chưa thu).
    - **`payment_summary`**: Tính toán sẵn tổng nợ, tổng số tiền đã đóng để AI trả lời nhanh chóng.

Toàn bộ dữ liệu này được serialize thành một dictionary và sau đó chuyển thành chuỗi JSON trong bước tiếp theo.

---

## 3. Cấu trúc System Prompt (Quy tắc Hệ thống)

System Prompt là "bộ não" điều khiển thái độ và độ chính xác của AI. Trong hàm `_build_system_prompt`, System Prompt được thiết kế với 2 phần:

### Phần 1: Các Quy tắc Bắt buộc (Hard Rules)
- Phải xưng hô là "Ban quản lý ký túc xá".
- **Chỉ được dùng dữ liệu từ CONTEXT**: Tuyệt đối không bịa đặt, suy đoán (hạn chế Hallucination).
- **Phân quyền truy cập**: Chỉ được trả lời dữ liệu (hợp đồng, hóa đơn) của đúng tài khoản đang đăng nhập trong CONTEXT. Nếu người dùng hỏi hóa đơn của người khác, phải từ chối ngay.
- Nếu câu hỏi nằm ngoài phạm vi hoạt động của ký túc xá, AI phải lịch sự từ chối.

### Phần 2: Khối Dữ liệu JSON (Data Block)
Bên dưới các quy tắc là một khối text chứa cấu trúc dữ liệu JSON vừa được sinh ra từ `_load_context()`. 

*Ví dụ:*
```json
"CONTEXT DATABASE":
{
  "access_scope": "student_self_only",
  "current_account": { "username": "nguyenvana", "role": "STUDENT" },
  "room_summary": { ...danh sách phòng... },
  "student_profile": { "full_name": "Nguyễn Văn A", "current_room": { "room_number": "101" } },
  "payment_summary": { "unpaid_total": "1,500,000 đ", "unpaid_count": 1 }
}
```

Nhờ có cấu trúc này, khi người dùng hỏi: *"Tháng này tôi còn nợ bao nhiêu?"*, AI sẽ đọc được `payment_summary.unpaid_total` là `1,500,000 đ` và trả lời chính xác dựa vào dữ liệu đó.

---

## 4. Tích hợp API (Google Gemini 1.5)

Hệ thống đang sử dụng API của Google Generative Language (Gemini Flash). Code không dùng thư viện ngoài (`google-generativeai`) mà sử dụng `urllib.request` mặc định của Python để tránh cồng kềnh và giảm dependencies.

- **URL Endpoint**: `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}`
- **Generation Config**:
  - `temperature: 0.2`: Giữ nhiệt độ thấp để AI trả lời có tính kỹ thuật, chính xác, không sáng tạo lan man.
  - `topP: 0.8`: Giới hạn lựa chọn token, giúp câu văn mượt mà nhưng vẫn bám sát chủ đề.
  - `maxOutputTokens: 700`: Ngăn AI trả lời quá dài dòng gây tốn thời gian và lãng phí token.

### Xử lý Ngoại lệ (Error Handling)
Hàm `_call_gemini_api` xử lý rất chi tiết các lỗi HTTP trả về. Nếu bạn nhập sai API Key, hoặc gửi request bị lỗi, hệ thống sẽ đọc gói tin báo lỗi (bằng JSON) từ Google, parse thông báo lỗi (`message`) và ném ra Exception thuần Việt (`Gemini API trả về lỗi: ...`) để thông báo lên UI.

## 5. Tổng kết

Cách tiếp cận này rất an toàn và bảo mật:
1. **Privacy By Design**: AI không được truy cập toàn bộ CSDL. Python code chỉ "bơm" (inject) thông tin hóa đơn của đúng người dùng đang đăng nhập vào bộ nhớ ngắn hạn của AI. Do đó, người dùng A không thể lừa AI để khai thác thông tin của người dùng B.
2. **Zero Setup Data Sync**: Bạn không cần phải xây dựng Vector Database, RAG (Retrieval-Augmented Generation) hay Fine-tuning. Vì dữ liệu (Data Context) được nhét trực tiếp vào câu lệnh (Prompt) mỗi khi query, AI luôn luôn có dữ liệu mới nhất (Real-time). Tiền nợ vừa được update, câu hỏi tiếp theo AI sẽ trả lời với con số mới ngay lập tức.