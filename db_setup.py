import sys

import pymysql

from config.database import Base, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, SessionLocal, engine
from models.user import User, UserRole
from utils.security import hash_password, is_password_hashed


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def create_db_if_not_exists():
    connection = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        port=int(DB_PORT),
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        connection.commit()
        print(f"Co so du lieu '{DB_NAME}' da san sang.")
    finally:
        connection.close()


def init_db():
    print("Dang khoi tao cac bang...")
    Base.metadata.create_all(bind=engine)
    print("Cac bang da duoc tao thanh cong.")

    session = SessionLocal()
    try:
        admin = session.query(User).filter_by(username="admin").first()
        if not admin:
            new_admin = User(
                username="admin",
                password=hash_password("admin123"),
                full_name="Quan tri vien",
                role=UserRole.ADMIN,
            )
            session.add(new_admin)
            session.commit()
            print("Da tao tai khoan quan tri mac dinh: admin / admin123")
        else:
            if not is_password_hashed(admin.password):
                admin.password = hash_password(admin.password or "admin123")
                session.commit()
                print("Da bao mat mat khau quan tri vien.")
            print("Tai khoan quan tri vien da ton tai.")
    except Exception as exc:
        print(f"Loi khi tao tai khoan quan tri: {exc}")
        session.rollback()
    finally:
        session.close()


def run_db_setup():
    try:
        create_db_if_not_exists()
        init_db()
        print("Hoan tat kiem tra va thiet lap co so du lieu.")
    except Exception as exc:
        print(f"Loi khi thiet lap co so du lieu: {exc}")


if __name__ == "__main__":
    run_db_setup()
