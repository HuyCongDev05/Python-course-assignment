import os
import sys
import pymysql
from dotenv import load_dotenv
from config.database import engine, Base, SessionLocal
from models.user import User, UserRole
from utils.security import hash_password, is_password_hashed

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Tải cấu hình (Load Config)
load_dotenv()

def create_db_if_not_exists():
    """Tạo cơ sở dữ liệu MySQL nếu chưa tồn tại"""
    host = os.getenv("DB_HOST", "localhost")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "12345678")
    db_name = os.getenv("DB_NAME", "dorm_management")
    port = int(os.getenv("DB_PORT", "3306"))

    connection = pymysql.connect(host=host, user=user, password=password, port=port)
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        connection.commit()
        print(f"Cơ sở dữ liệu '{db_name}' đã sẵn sàng.")
    finally:
        connection.close()

def init_db():
    """Khởi tạo các bảng và tài khoản quản trị (admin) mặc định"""
    print("Đang khởi tạo các bảng...")
    Base.metadata.create_all(bind=engine)
    print("Các bảng đã được tạo thành công.")

    # Tạo tài khoản quản trị mặc định (Default Admin)
    session = SessionLocal()
    try:
        admin = session.query(User).filter_by(username="admin").first()
        if not admin:
            new_admin = User(
                username="admin",
                password=hash_password("admin123"),
                full_name="Quản trị viên",
                role=UserRole.ADMIN
            )
            session.add(new_admin)
            session.commit()
            print("Đã tạo tài khoản quản trị mặc định: admin / admin123")
        else:
            if not is_password_hashed(admin.password):
                admin.password = hash_password(admin.password or "admin123")
                session.commit()
                print("Đã bảo mật mật khẩu quản trị viên.")
            print("Tài khoản quản trị viên đã tồn tại.")
    except Exception as e:
        print(f"Lỗi khi tạo tài khoản quản trị: {e}")
        session.rollback()
    session.commit()
    session.close()

def run_db_setup():
    """Hàm chạy toàn bộ quy trình thiết lập cơ sở dữ liệu"""
    try:
        create_db_if_not_exists()
        init_db()
        print("Hoàn tất kiểm tra và thiết lập cơ sở dữ liệu.")
    except Exception as e:
        print(f"Lỗi khi thiết lập cơ sở dữ liệu: {e}")

if __name__ == "__main__":
    run_db_setup()
