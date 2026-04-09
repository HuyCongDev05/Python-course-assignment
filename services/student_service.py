import re
from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from config.database import SessionLocal
from models import (
    Contract,
    Payment,
    PaymentStatus,
    PaymentType,
    Room,
    RoomStatus,
    Student,
    User,
    UserRole,
)
from utils.security import hash_password, is_password_hashed, verify_password


def _clean_text(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _coerce_room_status(value):
    if isinstance(value, RoomStatus):
        return value
    if value is None:
        return None
    return RoomStatus(value)


def _coerce_payment_type(value):
    if isinstance(value, PaymentType):
        return value
    return PaymentType(value)


def _coerce_payment_status(value):
    if isinstance(value, PaymentStatus):
        return value
    return PaymentStatus(value)


def _sync_room_status(room, preserve_maintenance=False):
    if room is None:
        return
    if room.current_occupancy < 0:
        room.current_occupancy = 0
    if preserve_maintenance and room.status == RoomStatus.MAINTENANCE and room.current_occupancy == 0:
        return
    room.status = RoomStatus.OCCUPIED if room.current_occupancy >= room.capacity else RoomStatus.AVAILABLE


def _calculate_contract_total(room_price, start_date, end_date):
    if not start_date or not end_date:
        return float(room_price or 0)

    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    if end_date.day >= start_date.day:
        months += 1
    months = max(months, 1)
    return float(room_price or 0) * months


def _calculate_default_end_date(start_date):
    """Trả về ngày kết thúc mặc định = 6 tháng sau ngày bắt đầu."""
    from datetime import date as _date
    month = start_date.month + 6
    year = start_date.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    day = min(start_date.day, last_day)
    return _date(year, month, day)


def _raise_value_error(message):
    raise ValueError(message)


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._]{3,23}$")
ONLINE_PAYMENT_PENDING_NOTE = "Đang chờ xác nhận thanh toán"
ONLINE_PAYMENT_CONFIRMED_NOTE = "Đã xác nhận thanh toán online"
LEGACY_ONLINE_PAYMENT_PENDING_NOTE = "Dang cho xac nhan thanh toan"
LEGACY_ONLINE_PAYMENT_CONFIRMED_NOTE = "Da xac nhan thanh toan online"


def is_online_payment_pending_note(note):
    return note in {ONLINE_PAYMENT_PENDING_NOTE, LEGACY_ONLINE_PAYMENT_PENDING_NOTE}


def is_online_payment_confirmed_note(note):
    return note in {ONLINE_PAYMENT_CONFIRMED_NOTE, LEGACY_ONLINE_PAYMENT_CONFIRMED_NOTE}


def _validate_registration_inputs(username, password, student_id, student):
    errors = []

    if not username:
        errors.append("Tên đăng nhập không được để trống.")
    elif not USERNAME_PATTERN.fullmatch(username):
        errors.append(
            "Tên đăng nhập phải dài 4-24 ký tự, bắt đầu bằng chữ cái và chỉ gồm chữ cái, số, dấu chấm hoặc gạch dưới."
        )

    if not password:
        errors.append("Mật khẩu không được để trống.")
    else:
        password_errors = []
        if len(password) < 8:
            password_errors.append("ít nhất 8 ký tự")
        if any(char.isspace() for char in password):
            password_errors.append("không chứa khoảng trắng")
        if not any(char.islower() for char in password):
            password_errors.append("có ít nhất 1 chữ thường")
        if not any(char.isupper() for char in password):
            password_errors.append("có ít nhất 1 chữ hoa")
        if not any(char.isdigit() for char in password):
            password_errors.append("có ít nhất 1 chữ số")
        if password_errors:
            errors.append("Mật khẩu phải " + ", ".join(password_errors) + ".")

    if not student_id:
        errors.append("Mã sinh viên không được để trống.")
    elif not student:
        errors.append("Mã sinh viên không tồn tại trong hệ thống.")

    return errors


class BaseService:
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()

    def _commit(self):
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise


class AuthService(BaseService):
    def login(self, username, password):
        user = self.db.query(User).filter_by(username=_clean_text(username)).first()
        if user and verify_password(password, user.password):
            if not is_password_hashed(user.password):
                user.password = hash_password(password)
                self._commit()
            return user
        return None

    def get_user_by_id(self, user_id):
        return self.db.get(User, user_id)


class StudentService(BaseService):
    def get_all_students(self, keyword=None):
        query = self.db.query(Student).options(joinedload(Student.room), joinedload(Student.user))
        keyword = _clean_text(keyword)
        if keyword:
            lookup = f"%{keyword}%"
            query = query.filter(
                or_(
                    Student.student_id.ilike(lookup),
                    Student.full_name.ilike(lookup),
                    Student.phone.ilike(lookup),
                    Student.email.ilike(lookup),
                )
            )
        return query.order_by(Student.id.desc()).all()

    def get_student_by_id(self, student_id):
        return (
            self.db.query(Student)
            .options(joinedload(Student.room), joinedload(Student.user))
            .filter(Student.id == student_id)
            .first()
        )

    def find_student_by_student_code(self, student_code):
        return self.db.query(Student).filter_by(student_id=_clean_text(student_code)).first()

    def add_student(self, student_data):
        data = {
            "student_id": _clean_text(student_data.get("student_id")),
            "full_name": _clean_text(student_data.get("full_name")),
            "gender": _clean_text(student_data.get("gender")),
            "phone": _clean_text(student_data.get("phone")),
            "email": _clean_text(student_data.get("email")),
            "hometown": _clean_text(student_data.get("hometown")),
        }

        if not data["student_id"] or not data["full_name"]:
            _raise_value_error("Mã sinh viên và họ tên là bắt buộc.")
        if self.find_student_by_student_code(data["student_id"]):
            _raise_value_error("Mã sinh viên đã tồn tại.")

        new_student = Student(**data)
        self.db.add(new_student)
        self._commit()
        self.db.refresh(new_student)
        return new_student

    def update_student(self, student_id, student_data):
        student = self.get_student_by_id(student_id)
        if not student:
            _raise_value_error("Không tìm thấy sinh viên.")

        student_code = _clean_text(student_data.get("student_id"))
        duplicate = self.find_student_by_student_code(student_code)
        if duplicate and duplicate.id != student.id:
            _raise_value_error("Mã sinh viên đã tồn tại.")

        for field in ["student_id", "full_name", "gender", "phone", "email", "hometown"]:
            if field in student_data:
                setattr(student, field, _clean_text(student_data.get(field)))

        if not student.student_id or not student.full_name:
            _raise_value_error("Mã sinh viên và họ tên là bắt buộc.")

        self._commit()
        return student

    def delete_student(self, student_id):
        student = self.get_student_by_id(student_id)
        if not student:
            return False

        related_contracts = self.db.query(Contract).filter(Contract.student_id == student.id).count()
        if related_contracts:
            _raise_value_error("Không thể xóa sinh viên đã có hợp đồng. Hãy kết thúc và lưu trữ hợp đồng trước.")

        if student.room:
            student.room.current_occupancy = max(0, student.room.current_occupancy - 1)
            _sync_room_status(student.room, preserve_maintenance=True)

        if student.user:
            self.db.delete(student.user)

        self.db.delete(student)
        self._commit()
        return True



    def get_available_rooms(self):
        return (
            self.db.query(Room)
            .filter(Room.current_occupancy < Room.capacity, Room.status == RoomStatus.AVAILABLE)
            .order_by(Room.room_number.asc())
            .all()
        )

    def get_student_by_user_id(self, user_id):
        return (
            self.db.query(Student)
            .options(joinedload(Student.room), joinedload(Student.user))
            .filter(Student.user_id == user_id)
            .first()
        )

    def register_student(self, username, password, student_id):
        try:
            username = _clean_text(username)
            password = _clean_text(password)
            student = self.find_student_by_student_code(student_id)

            validation_errors = _validate_registration_inputs(username, password, student_id, student)
            if validation_errors:
                return False, "\n".join(validation_errors), None
            if self.db.query(User).filter(User.username == username).first():
                return False, "Tên đăng nhập đã tồn tại.", None
            if student.user_id:
                return False, "Mã sinh viên này đã được kích hoạt tài khoản.", None

            new_user = User(
                username=username,
                password=hash_password(password),
                full_name=student.full_name,
                role=UserRole.STUDENT,
            )
            self.db.add(new_user)
            self.db.flush()

            student.user_id = new_user.id

            self._commit()
            self.db.refresh(new_user)
            return True, "Đăng ký thành công.", new_user
        except Exception as exc:
            self.db.rollback()
            return False, f"Lỗi: {exc}", None


class RoomService(BaseService):
    def get_all_rooms(self, keyword=None, status=None):
        query = self.db.query(Room)
        keyword = _clean_text(keyword)
        if keyword:
            lookup = f"%{keyword}%"
            query = query.filter(or_(Room.room_number.ilike(lookup), Room.room_type.ilike(lookup)))
        if status and status != "all":
            query = query.filter(Room.status == _coerce_room_status(status))
        return query.order_by(Room.room_number.asc()).all()

    def get_room_by_id(self, room_id):
        return self.db.get(Room, room_id)

    def add_room(self, room_data):
        room_number = _clean_text(room_data.get("room_number"))
        if not room_number:
            _raise_value_error("Số phòng là bắt buộc.")
        if self.db.query(Room).filter(Room.room_number == room_number).first():
            _raise_value_error("Số phòng đã tồn tại.")

        status = _coerce_room_status(room_data.get("status") or RoomStatus.AVAILABLE)
        room = Room(
            room_number=room_number,
            room_type=_clean_text(room_data.get("room_type")) or "Tiêu chuẩn",
            capacity=int(room_data.get("capacity") or 1),
            current_occupancy=int(room_data.get("current_occupancy") or 0),
            price=float(room_data.get("price") or 0),
            status=status,
        )

        if room.capacity < room.current_occupancy:
            _raise_value_error("Sức chứa không được nhỏ hơn số người đang ở.")
        if room.status == RoomStatus.MAINTENANCE and room.current_occupancy > 0:
            _raise_value_error("Không thể đưa phòng đang có người ở sang trạng thái bảo trì.")

        _sync_room_status(room, preserve_maintenance=True)
        self.db.add(room)
        self._commit()
        self.db.refresh(room)
        return room

    def update_room(self, room_id, room_data):
        room = self.get_room_by_id(room_id)
        if not room:
            _raise_value_error("Không tìm thấy phòng.")

        room_number = _clean_text(room_data.get("room_number"))
        duplicate = self.db.query(Room).filter(Room.room_number == room_number, Room.id != room.id).first()
        if duplicate:
            _raise_value_error("Số phòng đã tồn tại.")

        new_capacity = int(room_data.get("capacity") or room.capacity)
        new_occupancy = int(room_data.get("current_occupancy") or room.current_occupancy)
        new_status = _coerce_room_status(room_data.get("status") or room.status)

        if new_capacity < new_occupancy:
            _raise_value_error("Sức chứa không được nhỏ hơn số người đang ở.")
        if new_status == RoomStatus.MAINTENANCE and new_occupancy > 0:
            _raise_value_error("Chỉ có thể bảo trì khi phòng đang trống.")

        room.room_number = room_number
        room.room_type = _clean_text(room_data.get("room_type")) or room.room_type
        room.capacity = new_capacity
        room.current_occupancy = new_occupancy
        room.price = float(room_data.get("price") or room.price)
        room.status = new_status

        _sync_room_status(room, preserve_maintenance=True)
        self._commit()
        return room

    def delete_room(self, room_id):
        room = self.get_room_by_id(room_id)
        if not room:
            return False
        if room.current_occupancy > 0:
            _raise_value_error("Không thể xóa phòng đang có người ở.")
        if self.db.query(Contract).filter(Contract.room_id == room.id).count():
            _raise_value_error("Không thể xóa phòng đã có lịch sử hợp đồng.")

        self.db.delete(room)
        self._commit()
        return True

    def update_room_status(self, room_id, status):
        room = self.get_room_by_id(room_id)
        if not room:
            return False

        status = _coerce_room_status(status)
        if status == RoomStatus.MAINTENANCE and room.current_occupancy > 0:
            _raise_value_error("Chỉ có thể bảo trì khi phòng đang trống.")

        room.status = status
        _sync_room_status(room, preserve_maintenance=True)
        self._commit()
        return True

    def select_room_for_student(self, user_id, room_id, start_date=None, end_date=None):
        from datetime import date as _date

        student = (
            self.db.query(Student)
            .options(joinedload(Student.room), joinedload(Student.user))
            .filter(Student.user_id == user_id)
            .first()
        )
        if not student:
            _raise_value_error("Không tìm thấy hồ sơ sinh viên.")

        room = self.get_room_by_id(room_id)
        if not room:
            _raise_value_error("Không tìm thấy phòng.")

        active_contract = (
            self.db.query(Contract)
            .filter(Contract.student_id == student.id, Contract.status == "active")
            .first()
        )
        if active_contract and active_contract.room_id != room.id:
            _raise_value_error("Bạn đang có hợp đồng hiệu lực. Không thể tự đổi sang phòng khác.")
        if active_contract and active_contract.room_id == room.id:
            student.room_id = room.id
            self._commit()
            return student

        if room.status == RoomStatus.MAINTENANCE:
            _raise_value_error("Phòng đang bảo trì.")
        if student.room_id == room.id:
            return student
        if room.current_occupancy >= room.capacity:
            _raise_value_error("Phòng này đã đầy.")

        old_room = self.db.get(Room, student.room_id) if student.room_id else None
        if old_room and old_room.id != room.id:
            old_room.current_occupancy = max(0, old_room.current_occupancy - 1)
            _sync_room_status(old_room, preserve_maintenance=True)

        room.current_occupancy += 1
        student.room_id = room.id
        _sync_room_status(room)

        # --- Tạo hợp đồng và phiếu thanh toán tháng đầu ---
        contract_start = start_date or _date.today()
        contract_end = end_date or _calculate_default_end_date(contract_start)
        total_amount = _calculate_contract_total(room.price, contract_start, contract_end)

        new_contract = Contract(
            student_id=student.id,
            room_id=room.id,
            start_date=contract_start,
            end_date=contract_end,
            total_amount=total_amount,
            status="active",
        )
        self.db.add(new_contract)
        self.db.flush()  # lấy new_contract.id

        first_payment = Payment(
            contract_id=new_contract.id,
            amount=float(room.price),
            payment_type=PaymentType.ROOM_FEE,
            payment_date=contract_start,
            status=PaymentStatus.UNPAID,
            notes="Chưa xác nhận",
        )
        self.db.add(first_payment)
        # --------------------------------------------------

        self._commit()
        return student


class ContractService(BaseService):
    ACTIVE_STATUS = "active"

    def refresh_contract_statuses(self):
        today = date.today()
        changed = False
        active_contracts = (
            self.db.query(Contract)
            .options(joinedload(Contract.student), joinedload(Contract.room))
            .filter(Contract.status == self.ACTIVE_STATUS, Contract.end_date < today)
            .all()
        )

        for contract in active_contracts:
            contract.status = "expired"
            self._release_student(contract.student, contract.room)
            changed = True

        if changed:
            self._commit()

    def generate_monthly_payments(self):
        """Tự động tạo phiếu thanh toán tiền phòng cho tháng hiện tại
        nếu hợp đồng còn hiệu lực và chưa có phiếu nào trong tháng đó."""
        today = date.today()
        month_start = date(today.year, today.month, 1)

        active_contracts = (
            self.db.query(Contract)
            .options(joinedload(Contract.room), joinedload(Contract.payments))
            .filter(Contract.status == self.ACTIVE_STATUS)
            .all()
        )

        created = 0
        for contract in active_contracts:
            # Kiểm tra đã có phiếu ROOM_FEE trong tháng này chưa
            already_exists = any(
                p.payment_type == PaymentType.ROOM_FEE
                and p.payment_date >= month_start
                and p.payment_date <= today
                for p in contract.payments
            )
            if already_exists:
                continue

            room_price = float(contract.room.price) if contract.room else 0.0
            if room_price <= 0:
                continue

            new_payment = Payment(
                contract_id=contract.id,
                amount=room_price,
                payment_type=PaymentType.ROOM_FEE,
                payment_date=month_start,
                status=PaymentStatus.UNPAID,
                notes="Chưa xác nhận",
            )
            self.db.add(new_payment)
            created += 1

        if created:
            self._commit()
        return created

    def get_all_contracts(self, keyword=None, status=None):
        self.refresh_contract_statuses()

        query = (
            self.db.query(Contract)
            .options(joinedload(Contract.student), joinedload(Contract.room))
            .join(Student, Contract.student_id == Student.id)
            .join(Room, Contract.room_id == Room.id)
        )
        keyword = _clean_text(keyword)
        if keyword:
            lookup = f"%{keyword}%"
            query = query.filter(
                or_(
                    Student.full_name.ilike(lookup),
                    Student.student_id.ilike(lookup),
                    Room.room_number.ilike(lookup),
                )
            )
        if status and status != "all":
            query = query.filter(Contract.status == status)
        return query.order_by(Contract.start_date.desc(), Contract.id.desc()).all()

    def get_contract_by_id(self, contract_id):
        return (
            self.db.query(Contract)
            .options(joinedload(Contract.student), joinedload(Contract.room), joinedload(Contract.payments))
            .filter(Contract.id == contract_id)
            .first()
        )

    def get_assignable_students(self, include_student_id=None):
        students = self.db.query(Student).options(joinedload(Student.room), joinedload(Student.user)).order_by(Student.full_name.asc()).all()
        result = []
        for student in students:
            active_contract = (
                self.db.query(Contract)
                .filter(
                    Contract.student_id == student.id,
                    Contract.status == self.ACTIVE_STATUS,
                )
                .first()
            )
            if include_student_id and student.id == include_student_id:
                result.append(student)
                continue
            if not active_contract:
                result.append(student)
        return result

    def get_room_candidates(self, include_room_id=None):
        rooms = self.db.query(Room).order_by(Room.room_number.asc()).all()
        result = []
        for room in rooms:
            if include_room_id and room.id == include_room_id:
                result.append(room)
                continue
            if room.status != RoomStatus.MAINTENANCE and room.current_occupancy < room.capacity:
                result.append(room)
        return result

    def create_contract(self, contract_data):
        student = self.db.get(Student, contract_data.get("student_id"))
        room = self.db.get(Room, contract_data.get("room_id"))
        start_date = contract_data.get("start_date")
        end_date = contract_data.get("end_date")
        status = _clean_text(contract_data.get("status") or self.ACTIVE_STATUS)

        if not student or not room:
            _raise_value_error("Sinh viên hoặc phòng không tồn tại.")
        if not start_date or not end_date or start_date > end_date:
            _raise_value_error("Ngày hợp đồng không hợp lệ.")
        if status == self.ACTIVE_STATUS:
            self._ensure_active_contract_allowed(student.id, room.id)

        total_amount = float(contract_data.get("total_amount") or _calculate_contract_total(room.price, start_date, end_date))
        contract = Contract(
            student_id=student.id,
            room_id=room.id,
            start_date=start_date,
            end_date=end_date,
            total_amount=total_amount,
            status=status,
        )
        self.db.add(contract)
        self.db.flush()

        if status == self.ACTIVE_STATUS:
            self._assign_student(student, room)

        self._commit()
        self.db.refresh(contract)
        return contract

    def update_contract(self, contract_id, contract_data):
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            _raise_value_error("Không tìm thấy hợp đồng.")

        old_student = contract.student
        old_room = contract.room
        old_status = contract.status

        student = self.db.get(Student, contract_data.get("student_id"))
        room = self.db.get(Room, contract_data.get("room_id"))
        start_date = contract_data.get("start_date")
        end_date = contract_data.get("end_date")
        status = _clean_text(contract_data.get("status") or contract.status)

        if not student or not room:
            _raise_value_error("Sinh viên hoặc phòng không tồn tại.")
        if not start_date or not end_date or start_date > end_date:
            _raise_value_error("Ngày hợp đồng không hợp lệ.")

        if old_status == self.ACTIVE_STATUS and (
            old_student.id != student.id or old_room.id != room.id or status != self.ACTIVE_STATUS
        ):
            self._release_student(old_student, old_room)

        if status == self.ACTIVE_STATUS:
            self._ensure_active_contract_allowed(student.id, room.id, exclude_contract_id=contract.id)
            self._assign_student(student, room)

        contract.student_id = student.id
        contract.room_id = room.id
        contract.start_date = start_date
        contract.end_date = end_date
        contract.status = status
        contract.total_amount = float(contract_data.get("total_amount") or _calculate_contract_total(room.price, start_date, end_date))

        self._commit()
        return contract

    def terminate_contract(self, contract_id):
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            _raise_value_error("Không tìm thấy hợp đồng.")

        if contract.status == self.ACTIVE_STATUS:
            self._release_student(contract.student, contract.room)

        contract.status = "terminated"
        self._commit()
        return contract

    def delete_contract(self, contract_id):
        contract = self.get_contract_by_id(contract_id)
        if not contract:
            return False
        if contract.payments:
            _raise_value_error("Không thể xóa hợp đồng đã có thanh toán.")

        if contract.status == self.ACTIVE_STATUS:
            self._release_student(contract.student, contract.room)

        self.db.delete(contract)
        self._commit()
        return True

    def _ensure_active_contract_allowed(self, student_id, room_id, exclude_contract_id=None):
        active_contract_query = self.db.query(Contract).filter(
            Contract.student_id == student_id,
            Contract.status == self.ACTIVE_STATUS,
        )
        if exclude_contract_id:
            active_contract_query = active_contract_query.filter(Contract.id != exclude_contract_id)
        if active_contract_query.first():
            _raise_value_error("Sinh viên đang có hợp đồng còn hiệu lực.")

        room = self.db.get(Room, room_id)
        if room.status == RoomStatus.MAINTENANCE:
            _raise_value_error("Phòng đang bảo trì.")

    def _assign_student(self, student, room):
        old_room = self.db.get(Room, student.room_id) if student.room_id else None
        if old_room and old_room.id != room.id:
            old_room.current_occupancy = max(0, old_room.current_occupancy - 1)
            _sync_room_status(old_room, preserve_maintenance=True)

        if student.room_id != room.id:
            if room.current_occupancy >= room.capacity:
                _raise_value_error("Phòng đã đầy.")
            room.current_occupancy += 1

        student.room_id = room.id
        _sync_room_status(room)

    def _release_student(self, student, room):
        if not student or not room:
            return
        other_active_contract = (
            self.db.query(Contract)
            .filter(
                Contract.student_id == student.id,
                Contract.room_id == room.id,
                Contract.status == self.ACTIVE_STATUS,
            )
            .count()
        )
        if other_active_contract > 1:
            return

        if student.room_id == room.id:
            student.room_id = None
        room.current_occupancy = max(0, room.current_occupancy - 1)
        _sync_room_status(room, preserve_maintenance=True)


class PaymentService(BaseService):
    def get_all_payments(self, keyword=None, status=None):
        query = (
            self.db.query(Payment)
            .options(
                joinedload(Payment.contract).joinedload(Contract.student),
                joinedload(Payment.contract).joinedload(Contract.room),
            )
            .join(Contract, Payment.contract_id == Contract.id)
            .join(Student, Contract.student_id == Student.id)
            .join(Room, Contract.room_id == Room.id)
        )

        keyword = _clean_text(keyword)
        if keyword:
            lookup = f"%{keyword}%"
            query = query.filter(
                or_(
                    Student.full_name.ilike(lookup),
                    Student.student_id.ilike(lookup),
                    Room.room_number.ilike(lookup),
                )
            )
        if status and status != "all":
            query = query.filter(Payment.status == _coerce_payment_status(status))
        return query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()

    def get_payment_by_id(self, payment_id):
        return (
            self.db.query(Payment)
            .options(
                joinedload(Payment.contract).joinedload(Contract.student),
                joinedload(Payment.contract).joinedload(Contract.room),
            )
            .filter(Payment.id == payment_id)
            .first()
        )

    def get_contract_candidates(self, include_contract_id=None):
        contracts = (
            self.db.query(Contract)
            .options(joinedload(Contract.student), joinedload(Contract.room))
            .order_by(Contract.id.desc())
            .all()
        )
        result = []
        for contract in contracts:
            if include_contract_id and contract.id == include_contract_id:
                result.append(contract)
                continue
            if contract.status in {"active", "expired"}:
                result.append(contract)
        return result

    def create_payment(self, payment_data):
        contract = self.db.get(Contract, payment_data.get("contract_id"))
        if not contract:
            _raise_value_error("Không tìm thấy hợp đồng.")

        amount = float(payment_data.get("amount") or 0)
        if amount <= 0:
            _raise_value_error("Số tiền phải lớn hơn 0.")

        payment = Payment(
            contract_id=contract.id,
            amount=amount,
            payment_type=_coerce_payment_type(payment_data.get("payment_type") or PaymentType.ROOM_FEE),
            payment_date=payment_data.get("payment_date") or date.today(),
            status=_coerce_payment_status(payment_data.get("status") or PaymentStatus.UNPAID),
            notes=_clean_text(payment_data.get("notes")),
        )
        self.db.add(payment)
        self._commit()
        self.db.refresh(payment)
        return payment

    def update_payment(self, payment_id, payment_data):
        payment = self.get_payment_by_id(payment_id)
        if not payment:
            _raise_value_error("Không tìm thấy phiếu thanh toán.")

        contract = self.db.get(Contract, payment_data.get("contract_id"))
        if not contract:
            _raise_value_error("Không tìm thấy hợp đồng.")

        amount = float(payment_data.get("amount") or 0)
        if amount <= 0:
            _raise_value_error("Số tiền phải lớn hơn 0.")

        payment.contract_id = contract.id
        payment.amount = amount
        payment.payment_type = _coerce_payment_type(payment_data.get("payment_type") or payment.payment_type)
        payment.payment_date = payment_data.get("payment_date") or payment.payment_date
        payment.status = _coerce_payment_status(payment_data.get("status") or payment.status)
        payment.notes = _clean_text(payment_data.get("notes"))

        self._commit()
        return payment

    def mark_paid(self, payment_id):
        payment = self.get_payment_by_id(payment_id)
        if not payment:
            return False
        payment.status = PaymentStatus.PAID
        payment.payment_date = date.today()
        if is_online_payment_pending_note(payment.notes):
            payment.notes = ONLINE_PAYMENT_CONFIRMED_NOTE
        self._commit()
        return True

    def submit_online_payment_request(self, payment_id):
        payment = self.get_payment_by_id(payment_id)
        if not payment:
            _raise_value_error("KhÃ´ng tÃ¬m tháº¥y phiáº¿u thanh toÃ¡n.")
        if payment.status == PaymentStatus.PAID:
            _raise_value_error("Phiáº¿u nÃ y Ä‘Ã£ Ä‘Æ°á»£c xÃ¡c nháº­n thanh toÃ¡n.")
        if is_online_payment_pending_note(payment.notes):
            return payment

        payment.notes = ONLINE_PAYMENT_PENDING_NOTE
        self._commit()
        return payment

    def delete_payment(self, payment_id):
        payment = self.get_payment_by_id(payment_id)
        if not payment:
            return False
        self.db.delete(payment)
        self._commit()
        return True
