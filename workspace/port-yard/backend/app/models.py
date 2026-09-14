from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base


class ContainerStatus(str, enum.Enum):
    BOOKED = "BOOKED"          # 已预约未进场
    IN_YARD = "IN_YARD"        # 在场
    OUT = "OUT"                # 已出场


class Vessel(Base):
    """船期"""
    __tablename__ = "vessels"
    id = Column(Integer, primary_key=True)
    vessel_name = Column(String(64), nullable=False)
    voyage = Column(String(32), nullable=False)
    eta = Column(DateTime, nullable=False)   # 预计到港
    etd = Column(DateTime, nullable=False)   # 预计离港
    status = Column(String(16), default="SCHEDULED")  # SCHEDULED/BERTHED/DEPARTED

    containers = relationship("Container", back_populates="vessel")


class YardPosition(Base):
    """堆位: 区-排-列-层"""
    __tablename__ = "yard_positions"
    id = Column(Integer, primary_key=True)
    block = Column(String(8), nullable=False)   # 区, e.g. A
    bay = Column(Integer, nullable=False)       # 排
    row = Column(Integer, nullable=False)       # 列
    tier = Column(Integer, nullable=False)      # 层
    occupied = Column(Boolean, default=False)

    container = relationship("Container", back_populates="position", uselist=False)

    @property
    def code(self):
        return f"{self.block}{self.bay:02d}{self.row:02d}{self.tier}"


class Container(Base):
    """集装箱"""
    __tablename__ = "containers"
    id = Column(Integer, primary_key=True)
    container_no = Column(String(11), unique=True, nullable=False, index=True)  # ISO 6346
    size = Column(String(4), default="40")       # 20/40/45
    ctype = Column(String(4), default="GP")      # GP/HC/RF(冷藏)
    status = Column(String(16), default=ContainerStatus.BOOKED.value)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=True)
    position_id = Column(Integer, ForeignKey("yard_positions.id"), nullable=True)
    weight_t = Column(Float, default=0)
    consignee = Column(String(64), default="")   # 收货人/货主
    free_days = Column(Integer, default=7)       # 免堆存天数
    in_time = Column(DateTime, nullable=True)
    out_time = Column(DateTime, nullable=True)
    has_hold = Column(Boolean, default=False)    # 海关/查验扣箱
    created_at = Column(DateTime, default=datetime.utcnow)

    vessel = relationship("Vessel", back_populates="containers")
    position = relationship("YardPosition", back_populates="container")
    gate_records = relationship("GateRecord", back_populates="container")


class GateRecord(Base):
    """进出闸记录"""
    __tablename__ = "gate_records"
    id = Column(Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False)
    direction = Column(String(4), nullable=False)   # IN / OUT
    truck_no = Column(String(16), default="")
    driver = Column(String(32), default="")
    gate = Column(String(8), default="G1")
    time = Column(DateTime, default=datetime.utcnow)
    result = Column(String(16), default="OK")       # OK / REJECTED
    remark = Column(String(128), default="")

    container = relationship("Container", back_populates="gate_records")


class MoveRecord(Base):
    """移箱记录: 场内堆位变更可追溯"""
    __tablename__ = "move_records"
    id = Column(Integer, primary_key=True)
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False)
    from_code = Column(String(8), nullable=False)   # 原堆位
    to_code = Column(String(8), nullable=False)     # 新堆位
    reason = Column(String(128), default="")
    time = Column(DateTime, default=datetime.utcnow)

    container = relationship("Container")


class Appointment(Base):
    """进场预约: 计划时间 ± 容差 构成到场时段"""
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    container_no = Column(String(11), nullable=False, index=True)
    vessel_id = Column(Integer, ForeignKey("vessels.id"), nullable=True)
    planned_time = Column(DateTime, nullable=False)
    tolerance_hours = Column(Integer, default=2)   # 到场容差(小时)
    truck_no = Column(String(16), default="")
    status = Column(String(16), default="PENDING")  # PENDING/COMPLETED/CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)

    vessel = relationship("Vessel")
