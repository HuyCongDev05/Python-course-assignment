from sqlalchemy import Column, Date, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
import datetime
import enum
from config.database import Base

class PaymentType(enum.Enum):
    ROOM_FEE = "room_fee"
    ELECTRICITY = "electricity"
    WATER = "water"

class PaymentStatus(enum.Enum):
    PAID = "paid"
    UNPAID = "unpaid"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_type = Column(Enum(PaymentType), default=PaymentType.ROOM_FEE)
    payment_date = Column(Date, default=datetime.date.today)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID)
    notes = Column(String(255))

    # Các mối quan hệ (Relationships)
    contract = relationship("Contract", back_populates="payments")

    def __repr__(self):
        return f"<Payment(id={self.id}, type='{self.payment_type}', status='{self.status}')>"
