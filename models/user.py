from sqlalchemy import Column, Enum, Integer, String
import enum
from config.database import Base

class UserRole(enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    STUDENT = "student"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False) # Mật khẩu đã mã hóa
    full_name = Column(String(100))
    role = Column(Enum(UserRole), default=UserRole.STAFF)

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"
