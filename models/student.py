from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from config.database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(15))
    email = Column(String(100))
    gender = Column(String(10))
    hometown = Column(String(100))
    
    # Khóa ngoại liên kết
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    
    # Các mối quan hệ
    user = relationship("User")
    room = relationship("Room", back_populates="students")
    contracts = relationship("Contract", back_populates="student")

    def __repr__(self):
        return f"<Student(name='{self.full_name}', student_id='{self.student_id}')>"
