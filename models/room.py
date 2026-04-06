from sqlalchemy import Column, Enum, Float, Integer, String
from sqlalchemy.orm import relationship
import enum
from config.database import Base

class RoomStatus(enum.Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"

class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String(20), unique=True, index=True, nullable=False)
    room_type = Column(String(50)) # Ví dụ: 'Loại A', 'Loại B', 'Vip'
    capacity = Column(Integer, default=4)
    current_occupancy = Column(Integer, default=0)
    price = Column(Float, default=0.0)
    status = Column(Enum(RoomStatus), default=RoomStatus.AVAILABLE)

    # Các mối quan hệ (Relationships)
    students = relationship("Student", back_populates="room")
    contracts = relationship("Contract", back_populates="room")

    def __repr__(self):
        return f"<Room(number='{self.room_number}', status='{self.status}')>"
