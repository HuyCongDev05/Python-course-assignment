from models import PaymentStatus, PaymentType, RoomStatus


def format_currency(value):
    return f"{float(value or 0):,.0f} VNĐ"


def format_date(value):
    if not value:
        return "--"
    return value.strftime("%d/%m/%Y")


def room_status_label(status):
    if isinstance(status, RoomStatus):
        status = status.value
    return {
        "available": "Còn trống",
        "occupied": "Đã đầy",
        "maintenance": "Bảo trì",
    }.get(status, str(status))


def contract_status_label(status):
    return {
        "active": "Hiệu lực",
        "expired": "Hết hạn",
        "terminated": "Đã kết thúc",
    }.get(status, str(status))


def payment_type_label(payment_type):
    if isinstance(payment_type, PaymentType):
        payment_type = payment_type.value
    return {
        "room_fee": "Tiền phòng",
        "electricity": "Tiền điện",
        "water": "Tiền nước",
    }.get(payment_type, str(payment_type))


def payment_status_label(status):
    if isinstance(status, PaymentStatus):
        status = status.value
    return {
        "paid": "Đã thanh toán",
        "unpaid": "Chưa thanh toán",
    }.get(status, str(status))


def payment_note_label(note):
    if not note:
        return "--"
    return {
        "Dang cho xac nhan thanh toan": "Đang chờ xác nhận thanh toán",
        "Đang chờ xác nhận thanh toán": "Đang chờ xác nhận thanh toán",
        "Da xac nhan thanh toan online": "Đã xác nhận thanh toán online",
        "Đã xác nhận thanh toán online": "Đã xác nhận thanh toán online",
    }.get(note, str(note))
