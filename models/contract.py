from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
import datetime
from config.database import Base

class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    start_date = Column(Date, default=datetime.date.today)
    end_date = Column(Date, nullable=False)
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="active") # trạng thái: hiệu lực, hết hạn, hoặc đã chấm dứt

    # Các mối quan hệ
    student = relationship("Student", back_populates="contracts")
    room = relationship("Room", back_populates="contracts")
    payments = relationship("Payment", back_populates="contract")

    def __repr__(self):
        return f"<Contract(id={self.id}, student_id={self.student_id}, status='{self.status}')>"
