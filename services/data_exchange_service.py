import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from models import Room, RoomStatus, Student
from services.student_service import BaseService, RoomService, StudentService, _clean_text
from utils.app_settings import get_export_directory
from utils.formatters import room_status_label
from utils.xlsx_utils import read_xlsx_rows, write_xlsx


STUDENT_FILE_HEADERS = [
    "Mã sinh viên",
    "Họ và tên",
    "Giới tính",
    "Số điện thoại",
    "Email",
    "Quê quán",
]

ROOM_FILE_HEADERS = [
    "Số phòng",
    "Phân loại",
    "Sức chứa",
    "Đang ở",
    "Giá thuê/tháng",
    "Trạng thái",
]

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_PATTERN = re.compile(r"^\d{9,15}$")
GENDER_MAPPING = {
    "nam": "Nam",
    "nu": "Nữ",
    "khac": "Khác",
}
ROOM_STATUS_MAPPING = {
    "available": RoomStatus.AVAILABLE,
    "con trong": RoomStatus.AVAILABLE,
    "occupied": RoomStatus.OCCUPIED,
    "da day": RoomStatus.OCCUPIED,
    "maintenance": RoomStatus.MAINTENANCE,
    "bao tri": RoomStatus.MAINTENANCE,
}


@dataclass
class ImportSummary:
    success_count: int = 0
    issues: list[str] = field(default_factory=list)

    @property
    def skipped_count(self):
        return len(self.issues)


def _normalize_lookup_text(value):
    text = _clean_text(value) or ""
    text = unicodedata.normalize("NFD", str(text).casefold())
    text = "".join(character for character in text if unicodedata.category(character) != "Mn")
    return text.replace("đ", "d")


def _normalize_header_row(headers):
    return [str(header or "").replace("\ufeff", "").strip() for header in headers]


def _ensure_expected_headers(headers, expected_headers):
    normalized_headers = _normalize_header_row(headers)
    if normalized_headers != expected_headers:
        expected = ", ".join(expected_headers)
        actual = ", ".join(normalized_headers) if normalized_headers else "(trống)"
        raise ValueError(
            "File Excel không đúng mẫu.\n"
            f"Cột yêu cầu: {expected}\n"
            f"Cột hiện tại: {actual}"
        )


def _pad_row(values, size):
    row = list(values[:size])
    while len(row) < size:
        row.append("")
    return row


def _row_is_empty(values):
    return all(_clean_text(value) in {None, ""} for value in values)


def _string_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return _clean_text(value) or ""
    return _clean_text(str(value)) or ""


def _normalize_decimal(value, allow_float=False):
    if isinstance(value, bool):
        raise ValueError("giá trị kiểu đúng/sai không hợp lệ")

    if isinstance(value, (int, float, Decimal)):
        decimal_value = Decimal(str(value))
    else:
        text = _clean_text(value)
        if not text:
            raise ValueError("không được để trống")

        sanitized = str(text).strip()
        sanitized = (
            sanitized.replace("VNĐ", "")
            .replace("VND", "")
            .replace("vnđ", "")
            .replace("vnd", "")
            .replace("Đ", "")
            .replace("đ", "")
            .replace(" ", "")
        )

        comma_index = sanitized.rfind(",")
        dot_index = sanitized.rfind(".")
        if "," in sanitized and "." in sanitized:
            if comma_index > dot_index:
                sanitized = sanitized.replace(".", "").replace(",", ".")
            else:
                sanitized = sanitized.replace(",", "")
        elif "," in sanitized:
            if sanitized.count(",") > 1 or len(sanitized.split(",")[-1]) == 3:
                sanitized = sanitized.replace(",", "")
            else:
                sanitized = sanitized.replace(",", ".")
        elif "." in sanitized and (sanitized.count(".") > 1 or len(sanitized.split(".")[-1]) == 3):
            sanitized = sanitized.replace(".", "")

        try:
            decimal_value = Decimal(sanitized)
        except InvalidOperation as exc:
            raise ValueError("không phải số hợp lệ") from exc

    if not allow_float and decimal_value != decimal_value.to_integral_value():
        raise ValueError("phải là số nguyên")
    return decimal_value


def normalize_student_import_record(values):
    student_id, full_name, gender, phone, email, hometown = _pad_row(values, len(STUDENT_FILE_HEADERS))

    student_id = _string_value(student_id)
    full_name = _string_value(full_name)
    gender = _string_value(gender)
    phone = _string_value(phone)
    email = _string_value(email)
    hometown = _string_value(hometown)

    if not student_id:
        raise ValueError("Mã sinh viên không được để trống.")
    if len(student_id) > 20:
        raise ValueError("Mã sinh viên vượt quá 20 ký tự.")

    if not full_name:
        raise ValueError("Họ và tên không được để trống.")
    if len(full_name) > 100:
        raise ValueError("Họ và tên vượt quá 100 ký tự.")

    if gender:
        normalized_gender = GENDER_MAPPING.get(_normalize_lookup_text(gender))
        if not normalized_gender:
            raise ValueError("Giới tính chỉ được phép là Nam, Nữ hoặc Khác.")
        gender = normalized_gender

    if phone:
        if not PHONE_PATTERN.fullmatch(phone):
            raise ValueError("Số điện thoại phải gồm 9-15 chữ số.")
        if len(phone) > 15:
            raise ValueError("Số điện thoại vượt quá 15 ký tự.")

    if email:
        if len(email) > 100:
            raise ValueError("Email vượt quá 100 ký tự.")
        if not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Email không đúng định dạng.")

    if hometown and len(hometown) > 100:
        raise ValueError("Quê quán vượt quá 100 ký tự.")

    return {
        "student_id": student_id,
        "full_name": full_name,
        "gender": gender,
        "phone": phone,
        "email": email,
        "hometown": hometown,
    }


def normalize_room_import_record(values):
    room_number, room_type, capacity, current_occupancy, price, status = _pad_row(values, len(ROOM_FILE_HEADERS))

    room_number = _string_value(room_number)
    room_type = _string_value(room_type) or "Tiêu chuẩn"
    status_text = _string_value(status)

    if not room_number:
        raise ValueError("Số phòng không được để trống.")
    if len(room_number) > 20:
        raise ValueError("Số phòng vượt quá 20 ký tự.")

    if len(room_type) > 50:
        raise ValueError("Phân loại phòng vượt quá 50 ký tự.")

    try:
        capacity_value = int(_normalize_decimal(capacity))
    except ValueError as exc:
        raise ValueError(f"Sức chứa {exc}.") from exc

    try:
        occupancy_value = int(_normalize_decimal(current_occupancy))
    except ValueError as exc:
        raise ValueError(f"Số người đang ở {exc}.") from exc

    try:
        price_value = _normalize_decimal(price, allow_float=True)
    except ValueError as exc:
        raise ValueError(f"Giá thuê {exc}.") from exc

    if capacity_value <= 0:
        raise ValueError("Sức chứa phải lớn hơn 0.")
    if occupancy_value < 0:
        raise ValueError("Số người đang ở không được âm.")
    if occupancy_value > capacity_value:
        raise ValueError("Số người đang ở không được lớn hơn sức chứa.")
    if price_value < 0:
        raise ValueError("Giá thuê không được âm.")

    status_value = ROOM_STATUS_MAPPING.get(_normalize_lookup_text(status_text))
    if not status_value:
        raise ValueError("Trạng thái chỉ được phép là Còn trống, Đã đầy hoặc Bảo trì.")

    if status_value == RoomStatus.MAINTENANCE and occupancy_value != 0:
        raise ValueError("Phòng bảo trì phải có số người đang ở bằng 0.")
    if status_value == RoomStatus.OCCUPIED and occupancy_value != capacity_value:
        raise ValueError("Phòng đã đầy phải có số người đang ở bằng sức chứa.")
    if status_value == RoomStatus.AVAILABLE and occupancy_value >= capacity_value:
        raise ValueError("Phòng còn trống phải có số người đang ở nhỏ hơn sức chứa.")

    return {
        "room_number": room_number,
        "room_type": room_type,
        "capacity": capacity_value,
        "current_occupancy": occupancy_value,
        "price": float(price_value),
        "status": status_value.value,
    }


def student_record_signature(data):
    return (
        _normalize_lookup_text(data.get("student_id")),
        _normalize_lookup_text(data.get("full_name")),
        _normalize_lookup_text(data.get("gender")),
        _normalize_lookup_text(data.get("phone")),
        _normalize_lookup_text(data.get("email")),
        _normalize_lookup_text(data.get("hometown")),
    )


def room_record_signature(data):
    normalized_price = str(Decimal(str(data.get("price") or 0)).quantize(Decimal("0.01")))
    return (
        _normalize_lookup_text(data.get("room_number")),
        _normalize_lookup_text(data.get("room_type")),
        int(data.get("capacity") or 0),
        int(data.get("current_occupancy") or 0),
        normalized_price,
        _normalize_lookup_text(data.get("status")),
    )


class DataExchangeService(BaseService):
    def import_students_from_excel(self, file_path):
        headers, rows = read_xlsx_rows(file_path)
        _ensure_expected_headers(headers, STUDENT_FILE_HEADERS)

        existing_students = self.db.query(Student).all()
        known_codes = {_normalize_lookup_text(student.student_id) for student in existing_students}
        known_signatures = {
            student_record_signature(
                {
                    "student_id": student.student_id,
                    "full_name": student.full_name,
                    "gender": student.gender or "",
                    "phone": student.phone or "",
                    "email": student.email or "",
                    "hometown": student.hometown or "",
                }
            )
            for student in existing_students
        }

        summary = ImportSummary()
        student_service = StudentService(self.db)

        for row_number, raw_values in enumerate(rows, start=2):
            values = _pad_row(raw_values, len(STUDENT_FILE_HEADERS))
            if _row_is_empty(values):
                continue

            try:
                record = normalize_student_import_record(values)
                signature = student_record_signature(record)
                code_key = _normalize_lookup_text(record["student_id"])

                if signature in known_signatures:
                    raise ValueError("Dữ liệu trùng hoàn toàn với sinh viên đã có hoặc đã nạp trước đó.")
                if code_key in known_codes:
                    raise ValueError("Mã sinh viên đã tồn tại trong hệ thống hoặc trong file đang nạp.")

                student_service.add_student(record)
                known_codes.add(code_key)
                known_signatures.add(signature)
                summary.success_count += 1
            except Exception as exc:
                summary.issues.append(f"Dòng {row_number}: {exc}")

        return summary

    def import_rooms_from_excel(self, file_path):
        headers, rows = read_xlsx_rows(file_path)
        _ensure_expected_headers(headers, ROOM_FILE_HEADERS)

        existing_rooms = self.db.query(Room).all()
        known_numbers = {_normalize_lookup_text(room.room_number) for room in existing_rooms}
        known_signatures = {
            room_record_signature(
                {
                    "room_number": room.room_number,
                    "room_type": room.room_type or "Tiêu chuẩn",
                    "capacity": room.capacity or 0,
                    "current_occupancy": room.current_occupancy or 0,
                    "price": room.price or 0,
                    "status": room.status.value if room.status else RoomStatus.AVAILABLE.value,
                }
            )
            for room in existing_rooms
        }

        summary = ImportSummary()
        room_service = RoomService(self.db)

        for row_number, raw_values in enumerate(rows, start=2):
            values = _pad_row(raw_values, len(ROOM_FILE_HEADERS))
            if _row_is_empty(values):
                continue

            try:
                record = normalize_room_import_record(values)
                signature = room_record_signature(record)
                room_key = _normalize_lookup_text(record["room_number"])

                if signature in known_signatures:
                    raise ValueError("Dữ liệu trùng hoàn toàn với phòng đã có hoặc đã nạp trước đó.")
                if room_key in known_numbers:
                    raise ValueError("Số phòng đã tồn tại trong hệ thống hoặc trong file đang nạp.")

                room_service.add_room(record)
                known_numbers.add(room_key)
                known_signatures.add(signature)
                summary.success_count += 1
            except Exception as exc:
                summary.issues.append(f"Dòng {row_number}: {exc}")

        return summary

    def export_students_to_excel(self, directory=None):
        export_directory = directory or get_export_directory()
        rows = [
            [
                student.student_id,
                student.full_name,
                student.gender or "",
                student.phone or "",
                student.email or "",
                student.hometown or "",
            ]
            for student in self.db.query(Student).order_by(Student.student_id.asc()).all()
        ]

        file_path = self._build_export_path(export_directory, "sinh_vien")
        write_xlsx(file_path, "SinhVien", STUDENT_FILE_HEADERS, rows)
        return file_path

    def export_rooms_to_excel(self, directory=None):
        rows = [
            [
                room.room_number,
                room.room_type or "Tiêu chuẩn",
                room.capacity or 0,
                room.current_occupancy or 0,
                int(room.price) if float(room.price or 0).is_integer() else room.price or 0,
                room_status_label(room.status),
            ]
            for room in self.db.query(Room).order_by(Room.room_number.asc()).all()
        ]

        export_directory = directory or get_export_directory()
        file_path = self._build_export_path(export_directory, "phong")
        write_xlsx(file_path, "Phong", ROOM_FILE_HEADERS, rows)
        return file_path

    def _build_export_path(self, directory, prefix):
        os.makedirs(directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(directory, f"{prefix}_{timestamp}.xlsx")
