import json
import os
from urllib import error, parse, request

from sqlalchemy.orm import joinedload

from config.database import SessionLocal
from models import Contract, Payment, PaymentStatus, Room, RoomStatus, Student, User, UserRole
from utils.formatters import (
    contract_status_label,
    format_currency,
    format_date,
    payment_note_label,
    payment_status_label,
    payment_type_label,
    room_status_label,
)


class DormChatService:
    DEFAULT_MODEL = "gemini-2.5-flash"
    API_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        self.model = os.getenv("GOOGLE_AI_STUDIO_MODEL", self.DEFAULT_MODEL)

    def ask(self, user_id, question):
        question = (question or "").strip()
        if not question:
            raise ValueError("Vui lòng nhập nội dung cần hỏi.")

        context = self._load_context(user_id)
        if not self.api_key:
            raise RuntimeError("Chưa cấu hình GOOGLE_AI_STUDIO_API_KEY trong file .env.")

        payload = {
            "systemInstruction": {
                "parts": [
                    {
                        "text": self._build_system_prompt(context),
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": question}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "maxOutputTokens": 900,
            },
        }

        response_payload = self._call_gemini_api(payload)
        answer = self._extract_answer(response_payload)
        if not answer:
            raise RuntimeError("Gemini API không trả về nội dung hợp lệ.")
        return answer.strip()

    def _call_gemini_api(self, payload):
        encoded_model = parse.quote(self.model, safe="")
        encoded_key = parse.quote(self.api_key, safe="")
        url = f"{self.API_TEMPLATE.format(model=encoded_model)}?key={encoded_key}"

        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(message)
                message = payload.get("error", {}).get("message") or message
            except json.JSONDecodeError:
                pass
            raise RuntimeError(f"Gemini API trả về lỗi: {message}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Không thể kết nối tới Gemini API: {exc.reason}") from exc

    def _extract_answer(self, response_payload):
        for candidate in response_payload.get("candidates", []):
            content = candidate.get("content", {})
            texts = []
            for part in content.get("parts", []):
                text = (part.get("text") or "").strip()
                if text:
                    texts.append(text)
            if texts:
                return "\n".join(texts)

        prompt_feedback = response_payload.get("promptFeedback", {})
        block_reason = prompt_feedback.get("blockReason")
        if block_reason:
            raise RuntimeError(f"Yêu cầu bị Gemini chặn: {block_reason}")
        return ""

    def _load_context(self, user_id):
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise RuntimeError("Không tìm thấy tài khoản đang đăng nhập.")

            current_role = user.role or UserRole.STAFF
            current_account = self._serialize_current_account(user)
            schema = self._build_schema_catalog()
            rooms = db.query(Room).order_by(Room.room_number.asc()).all()

            if current_role == UserRole.ADMIN:
                return self._build_admin_context(db, current_account, rooms, schema)
            if current_role == UserRole.STAFF:
                return self._build_staff_context(db, current_account, rooms, schema)

            student = (
                db.query(Student)
                .options(joinedload(Student.room), joinedload(Student.user))
                .filter(Student.user_id == user.id)
                .first()
            )
            return self._build_student_context(db, current_account, rooms, schema, student)

    def _build_student_context(self, db, current_account, rooms, schema, student):
        context = {
            "access_scope": "student_self_only" if student else "student_general_info_only",
            "current_account": current_account,
            "accessible_tables": ["rooms"],
            "restricted_tables": ["users", "students", "contracts", "payments"],
            "access_rules": [
                "Chi duoc tra loi du lieu lien quan truc tiep den tai khoan sinh vien dang dang nhap.",
                "Khong tiet lo du lieu cua sinh vien khac, ke ca khi nguoi dung hoi truc tiep.",
                "Bang users khong bao gio duoc phep lo mat khau.",
            ],
            "database_schema": schema,
            "table_row_counts": {
                "rooms": len(rooms),
                "students": 1 if student else 0,
                "contracts": 0,
                "payments": 0,
            },
            "room_summary": self._serialize_room_summary(rooms),
            "student_profile": None,
            "payment_summary": {
                "paid_total": format_currency(0),
                "unpaid_total": format_currency(0),
                "paid_count": 0,
                "unpaid_count": 0,
            },
            "tables": {
                "rooms": [self._serialize_room(room) for room in rooms],
                "students": [],
                "contracts": [],
                "payments": [],
            },
        }

        if not student:
            return context

        contracts = (
            db.query(Contract)
            .options(joinedload(Contract.student), joinedload(Contract.room))
            .filter(Contract.student_id == student.id)
            .order_by(Contract.start_date.desc(), Contract.id.desc())
            .all()
        )
        payments = (
            db.query(Payment)
            .options(
                joinedload(Payment.contract).joinedload(Contract.student),
                joinedload(Payment.contract).joinedload(Contract.room),
            )
            .join(Contract, Payment.contract_id == Contract.id)
            .filter(Contract.student_id == student.id)
            .order_by(Payment.payment_date.desc(), Payment.id.desc())
            .all()
        )

        paid_total = sum(float(item.amount or 0) for item in payments if item.status == PaymentStatus.PAID)
        unpaid_total = sum(float(item.amount or 0) for item in payments if item.status == PaymentStatus.UNPAID)

        context["accessible_tables"] = ["rooms", "students", "contracts", "payments"]
        context["restricted_tables"] = ["users"]
        context["table_row_counts"].update(
            {
                "students": 1,
                "contracts": len(contracts),
                "payments": len(payments),
            }
        )
        context["student_profile"] = self._serialize_student(student)
        context["tables"]["students"] = [self._serialize_student(student)]
        context["tables"]["contracts"] = [self._serialize_contract(item) for item in contracts]
        context["tables"]["payments"] = [self._serialize_payment(item) for item in payments]
        context["payment_summary"] = {
            "paid_total": format_currency(paid_total),
            "unpaid_total": format_currency(unpaid_total),
            "paid_count": sum(1 for item in payments if item.status == PaymentStatus.PAID),
            "unpaid_count": sum(1 for item in payments if item.status == PaymentStatus.UNPAID),
        }
        return context

    def _build_staff_context(self, db, current_account, rooms, schema):
        students = (
            db.query(Student)
            .options(joinedload(Student.room), joinedload(Student.user))
            .order_by(Student.id.desc())
            .all()
        )
        contracts = (
            db.query(Contract)
            .options(joinedload(Contract.student), joinedload(Contract.room))
            .order_by(Contract.start_date.desc(), Contract.id.desc())
            .all()
        )
        payments = (
            db.query(Payment)
            .options(
                joinedload(Payment.contract).joinedload(Contract.student),
                joinedload(Payment.contract).joinedload(Contract.room),
            )
            .order_by(Payment.payment_date.desc(), Payment.id.desc())
            .all()
        )

        return {
            "access_scope": "staff_operational_tables",
            "current_account": current_account,
            "accessible_tables": ["students", "rooms", "contracts", "payments"],
            "restricted_tables": ["users", "users.password"],
            "access_rules": [
                "Tai khoan STAFF duoc tra loi tren du lieu van hanh cua ky tuc xa.",
                "Du lieu bang users khong nam trong pham vi truy cap cua STAFF.",
                "Neu nguoi dung hoi thong tin ngoai cac bang duoc cap quyen, phai tu choi ngan gon.",
            ],
            "database_schema": schema,
            "table_row_counts": {
                "students": len(students),
                "rooms": len(rooms),
                "contracts": len(contracts),
                "payments": len(payments),
            },
            "room_summary": self._serialize_room_summary(rooms),
            "global_summary": self._serialize_global_summary(students, rooms, contracts, payments),
            "tables": {
                "students": [self._serialize_student(item) for item in students],
                "rooms": [self._serialize_room(item) for item in rooms],
                "contracts": [self._serialize_contract(item) for item in contracts],
                "payments": [self._serialize_payment(item) for item in payments],
            },
        }

    def _build_admin_context(self, db, current_account, rooms, schema):
        users = db.query(User).order_by(User.id.asc()).all()
        students = (
            db.query(Student)
            .options(joinedload(Student.room), joinedload(Student.user))
            .order_by(Student.id.desc())
            .all()
        )
        contracts = (
            db.query(Contract)
            .options(joinedload(Contract.student), joinedload(Contract.room))
            .order_by(Contract.start_date.desc(), Contract.id.desc())
            .all()
        )
        payments = (
            db.query(Payment)
            .options(
                joinedload(Payment.contract).joinedload(Contract.student),
                joinedload(Payment.contract).joinedload(Contract.room),
            )
            .order_by(Payment.payment_date.desc(), Payment.id.desc())
            .all()
        )

        student_lookup_by_user_id = {item.user_id: item for item in students if item.user_id}

        return {
            "access_scope": "admin_all_tables",
            "current_account": current_account,
            "accessible_tables": ["users", "students", "rooms", "contracts", "payments"],
            "restricted_tables": ["users.password"],
            "access_rules": [
                "Tai khoan ADMIN duoc tra loi tren tat ca bang hien co trong CONTEXT.",
                "Bang users da bi loai bo cot mat khau, khong duoc suy doan hay tiet lo thong tin mat khau duoi moi hinh thuc.",
                "Neu du lieu khong co trong CONTEXT hien tai thi phai noi ro he thong chua co du lieu do.",
            ],
            "database_schema": schema,
            "table_row_counts": {
                "users": len(users),
                "students": len(students),
                "rooms": len(rooms),
                "contracts": len(contracts),
                "payments": len(payments),
            },
            "room_summary": self._serialize_room_summary(rooms),
            "global_summary": self._serialize_global_summary(students, rooms, contracts, payments, users),
            "tables": {
                "users": [self._serialize_user(item, student_lookup_by_user_id.get(item.id)) for item in users],
                "students": [self._serialize_student(item) for item in students],
                "rooms": [self._serialize_room(item) for item in rooms],
                "contracts": [self._serialize_contract(item) for item in contracts],
                "payments": [self._serialize_payment(item) for item in payments],
            },
        }

    def _serialize_current_account(self, user):
        return {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name or user.username,
            "role": self._enum_value(user.role),
        }

    def _build_schema_catalog(self):
        return {
            "users": {
                "description": "Tai khoan dang nhap cua he thong, da an cot mat khau khi dua vao chatbot.",
                "columns": [
                    "id",
                    "username",
                    "full_name",
                    "role",
                    "linked_student_id",
                    "linked_student_code",
                    "linked_student_name",
                ],
            },
            "students": {
                "description": "Ho so sinh vien luu tru.",
                "columns": [
                    "id",
                    "student_id",
                    "full_name",
                    "gender",
                    "phone",
                    "email",
                    "hometown",
                    "user_id",
                    "username",
                    "room_id",
                    "room_number",
                ],
            },
            "rooms": {
                "description": "Thong tin phong o, suc chua va gia phong.",
                "columns": [
                    "room_id",
                    "room_number",
                    "room_type",
                    "capacity",
                    "current_occupancy",
                    "available_slots",
                    "price",
                    "price_display",
                    "status_code",
                    "status_label",
                ],
            },
            "contracts": {
                "description": "Hop dong luu tru giua sinh vien va phong.",
                "columns": [
                    "contract_id",
                    "student_db_id",
                    "student_code",
                    "student_name",
                    "room_id",
                    "room_number",
                    "start_date",
                    "start_date_iso",
                    "end_date",
                    "end_date_iso",
                    "total_amount",
                    "total_amount_display",
                    "status_code",
                    "status_label",
                ],
            },
            "payments": {
                "description": "Cac phieu thanh toan tien phong, dien, nuoc.",
                "columns": [
                    "payment_id",
                    "contract_id",
                    "student_db_id",
                    "student_code",
                    "student_name",
                    "room_id",
                    "room_number",
                    "amount",
                    "amount_display",
                    "payment_type_code",
                    "payment_type_label",
                    "payment_date",
                    "payment_date_iso",
                    "status_code",
                    "status_label",
                    "notes",
                    "notes_display",
                ],
            },
        }

    def _serialize_room_summary(self, rooms):
        available_rooms = [
            room
            for room in rooms
            if self._enum_value(room.status) != RoomStatus.MAINTENANCE.value
            and self._room_occupancy(room) < self._room_capacity(room)
        ]
        return {
            "total_rooms": len(rooms),
            "available_rooms": sum(1 for room in rooms if self._enum_value(room.status) == RoomStatus.AVAILABLE.value),
            "occupied_rooms": sum(1 for room in rooms if self._enum_value(room.status) == RoomStatus.OCCUPIED.value),
            "maintenance_rooms": sum(1 for room in rooms if self._enum_value(room.status) == RoomStatus.MAINTENANCE.value),
            "total_capacity": sum(self._room_capacity(room) for room in rooms),
            "total_occupancy": sum(self._room_occupancy(room) for room in rooms),
            "vacancy_candidates": [self._serialize_room(room) for room in available_rooms],
        }

    def _serialize_global_summary(self, students, rooms, contracts, payments, users=None):
        unpaid_payments = [item for item in payments if item.status == PaymentStatus.UNPAID]
        paid_payments = [item for item in payments if item.status == PaymentStatus.PAID]
        return {
            "total_users": len(users) if users is not None else None,
            "total_students": len(students),
            "total_rooms": len(rooms),
            "total_contracts": len(contracts),
            "active_contracts": sum(1 for item in contracts if item.status == "active"),
            "expired_contracts": sum(1 for item in contracts if item.status == "expired"),
            "terminated_contracts": sum(1 for item in contracts if item.status == "terminated"),
            "total_payments": len(payments),
            "paid_payments": len(paid_payments),
            "unpaid_payments": len(unpaid_payments),
            "paid_total": format_currency(sum(float(item.amount or 0) for item in paid_payments)),
            "unpaid_total": format_currency(sum(float(item.amount or 0) for item in unpaid_payments)),
            "total_capacity": sum(self._room_capacity(item) for item in rooms),
            "total_occupancy": sum(self._room_occupancy(item) for item in rooms),
        }

    def _serialize_user(self, user, linked_student=None):
        return {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name or "--",
            "role": self._enum_value(user.role),
            "linked_student_id": linked_student.id if linked_student else None,
            "linked_student_code": linked_student.student_id if linked_student else None,
            "linked_student_name": linked_student.full_name if linked_student else None,
        }

    def _serialize_student(self, student):
        return {
            "id": student.id,
            "student_id": student.student_id,
            "full_name": student.full_name,
            "gender": student.gender or "--",
            "phone": student.phone or "--",
            "email": student.email or "--",
            "hometown": student.hometown or "--",
            "user_id": student.user_id,
            "username": student.user.username if student.user else None,
            "room_id": student.room_id,
            "room_number": student.room.room_number if student.room else None,
            "current_room": self._serialize_room(student.room),
        }

    def _serialize_room(self, room):
        if not room:
            return None

        capacity = self._room_capacity(room)
        occupancy = self._room_occupancy(room)
        return {
            "room_id": room.id,
            "room_number": room.room_number,
            "room_type": room.room_type or "--",
            "capacity": capacity,
            "current_occupancy": occupancy,
            "available_slots": max(capacity - occupancy, 0),
            "price": float(room.price or 0),
            "price_display": format_currency(room.price),
            "status_code": self._enum_value(room.status),
            "status_label": room_status_label(room.status),
        }

    def _serialize_contract(self, contract):
        return {
            "contract_id": contract.id,
            "student_db_id": contract.student.id if contract.student else None,
            "student_code": contract.student.student_id if contract.student else None,
            "student_name": contract.student.full_name if contract.student else "--",
            "room_id": contract.room.id if contract.room else None,
            "room_number": contract.room.room_number if contract.room else "--",
            "start_date": format_date(contract.start_date),
            "start_date_iso": contract.start_date.isoformat() if contract.start_date else None,
            "end_date": format_date(contract.end_date),
            "end_date_iso": contract.end_date.isoformat() if contract.end_date else None,
            "total_amount": float(contract.total_amount or 0),
            "total_amount_display": format_currency(contract.total_amount),
            "status_code": contract.status,
            "status_label": contract_status_label(contract.status),
        }

    def _serialize_payment(self, payment):
        contract = payment.contract
        student = contract.student if contract else None
        room = contract.room if contract else None
        return {
            "payment_id": payment.id,
            "contract_id": payment.contract_id,
            "student_db_id": student.id if student else None,
            "student_code": student.student_id if student else None,
            "student_name": student.full_name if student else "--",
            "room_id": room.id if room else None,
            "room_number": room.room_number if room else "--",
            "amount": float(payment.amount or 0),
            "amount_display": format_currency(payment.amount),
            "payment_type_code": self._enum_value(payment.payment_type),
            "payment_type_label": payment_type_label(payment.payment_type),
            "payment_date": format_date(payment.payment_date),
            "payment_date_iso": payment.payment_date.isoformat() if payment.payment_date else None,
            "status_code": self._enum_value(payment.status),
            "status_label": payment_status_label(payment.status),
            "notes": payment.notes,
            "notes_display": payment_note_label(payment.notes),
        }

    def _room_capacity(self, room):
        return int(room.capacity or 0)

    def _room_occupancy(self, room):
        return int(room.current_occupancy or 0)

    def _enum_value(self, value):
        return getattr(value, "value", value)

    def _build_system_prompt(self, context):
        context_json = json.dumps(context, ensure_ascii=False, indent=2)
        accessible_tables = ", ".join(context.get("accessible_tables", [])) or "không có bảng nào"
        restricted_tables = ", ".join(context.get("restricted_tables", [])) or "không có"

        return (
            "Bạn là trợ lý AI của Ban quản lý ký túc xá sinh viên.\n"
            "Quy tắc bắt buộc:\n"
            "1. Mỗi câu trả lời phải chỉ dựa trên dữ liệu database trong CONTEXT DATABASE ở dưới.\n"
            "2. Không bịa thông tin, không suy đoán ngoài dữ liệu đang có.\n"
            f"3. Các bảng được cấp quyền hiện tại là: {accessible_tables}. Các bảng hoặc cột bị hạn chế là: {restricted_tables}.\n"
            "4. Có thể trả lời câu hỏi về bất kỳ dữ liệu, thống kê, lọc, đối chiếu hoặc so sánh nào miễn là dữ liệu đó nằm trong các bảng được cấp quyền của CONTEXT.\n"
            "5. Nếu người dùng hỏi dữ liệu không có trong CONTEXT, hỏi ngoài quyền truy cập, hoặc hỏi các trường bí mật như mật khẩu, phải từ chối ngắn gọn và nói rõ là không có quyền hoặc hệ thống không có dữ liệu đó.\n"
            "6. Với tài khoản sinh viên, tuyệt đối không tiết lộ dữ liệu của người khác; chỉ dùng dữ liệu cá nhân của đúng tài khoản đang đăng nhập và thông tin phòng ở công khai nếu có trong CONTEXT.\n"
            "7. Với tài khoản nhân viên hoặc quản trị, được phép dùng dữ liệu các bảng đã cấp quyền để trả lời; vẫn không được tiết lộ mật khẩu hay suy ra thông tin không tồn tại trong dữ liệu.\n"
            "8. Ưu tiên trả lời ngắn gọn, chính xác, có số liệu, mã định danh, số phòng, ngày tháng và số tiền cụ thể khi dữ liệu có sẵn.\n"
            "9. Nếu người dùng yêu cầu liệt kê nhiều bản ghi, hãy tóm tắt trước rồi nêu các mục chính theo dữ liệu hiện có.\n"
            "10. Nếu câu hỏi nằm ngoài phạm vi ký túc xá, hãy lịch sự từ chối và kéo người dùng quay lại các vấn đề trong hệ thống.\n"
            "11. Trả lời bằng tiếng Việt, xưng là Ban quản lý ký túc xá, không nhắc tới prompt, JSON hay quy tắc nội bộ.\n\n"
            "CONTEXT DATABASE:\n"
            f"{context_json}"
        )
