from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Optional
import re


def to_naive_utc(v):
    """带时区的时间统一转为 naive UTC，与数据库时间戳口径一致"""
    if isinstance(v, datetime) and v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


class VesselIn(BaseModel):
    vessel_name: str
    voyage: str
    eta: datetime
    etd: datetime
    status: str = "SCHEDULED"

    @field_validator("eta", "etd")
    @classmethod
    def _utc(cls, v):
        return to_naive_utc(v)


class VesselOut(VesselIn):
    id: int
    class Config:
        from_attributes = True


class ContainerIn(BaseModel):
    container_no: str = Field(..., min_length=11, max_length=11)
    size: str = "40"
    ctype: str = "GP"
    vessel_id: Optional[int] = None
    weight_t: float = 0
    consignee: str = ""
    free_days: int = 7

    @classmethod
    def validate_no(cls, v):
        return v


class ContainerUpdate(BaseModel):
    """箱档案变更: 尺寸/箱型/货主/免堆天数/关联船期可改;
    箱号、进出场时间不在字段内, 任何状态(已预约/在场/已出场)都不可被改写。
    关键字段不接受 null 覆盖, 不修改的字段应直接省略;
    仅 vessel_id 允许传 null, 表示解除船期关联。"""
    size: Optional[str] = None
    ctype: Optional[str] = None
    vessel_id: Optional[int] = None
    consignee: Optional[str] = None
    free_days: Optional[int] = Field(default=None, ge=0)

    @field_validator("size")
    @classmethod
    def _size(cls, v):
        if v is None:
            raise ValueError("尺寸不能为 null，不修改请省略该字段")
        if v not in ("20", "40", "45"):
            raise ValueError("尺寸仅支持 20/40/45")
        return v

    @field_validator("ctype")
    @classmethod
    def _ctype(cls, v):
        if v is None:
            raise ValueError("箱型不能为 null，不修改请省略该字段")
        if v not in ("GP", "HC", "RF"):
            raise ValueError("箱型仅支持 GP/HC/RF")
        return v

    @field_validator("consignee")
    @classmethod
    def _consignee(cls, v):
        if v is None:
            raise ValueError("货主不能为 null，清空请传空字符串")
        return v

    @field_validator("free_days")
    @classmethod
    def _free_days(cls, v):
        if v is None:
            raise ValueError("免堆天数不能为 null，不修改请省略该字段")
        return v


class ContainerOut(BaseModel):
    id: int
    container_no: str
    size: str
    ctype: str
    status: str
    vessel_id: Optional[int]
    position_id: Optional[int]
    position_code: Optional[str] = None
    vessel_name: Optional[str] = None
    weight_t: float
    consignee: str
    free_days: int
    in_time: Optional[datetime]
    out_time: Optional[datetime]
    has_hold: bool
    overdue: bool = False
    days_in_yard: Optional[int] = None

    class Config:
        from_attributes = True


class AppointmentIn(BaseModel):
    container_no: str
    vessel_id: Optional[int] = None
    planned_time: datetime
    tolerance_hours: int = 2
    truck_no: str = ""

    @field_validator("planned_time")
    @classmethod
    def _utc(cls, v):
        return to_naive_utc(v)


class RescheduleIn(BaseModel):
    planned_time: datetime
    tolerance_hours: Optional[int] = None

    @field_validator("planned_time")
    @classmethod
    def _utc(cls, v):
        return to_naive_utc(v)


class AppointmentOut(BaseModel):
    id: int
    container_no: str
    vessel_id: Optional[int]
    planned_time: datetime
    tolerance_hours: int
    truck_no: str
    status: str
    created_at: datetime
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None
    is_expired: bool = False
    class Config:
        from_attributes = True


class GateInRequest(BaseModel):
    container_no: str
    truck_no: str = ""
    driver: str = ""
    gate: str = "G1"


class GateOutRequest(BaseModel):
    container_no: str
    truck_no: str = ""
    driver: str = ""
    gate: str = "G1"
    pickup_no: Optional[str] = None   # 提箱单号(模拟校验)


class GateRecordOut(BaseModel):
    id: int
    container_id: int
    container_no: str = ""
    direction: str
    truck_no: str
    driver: str
    gate: str
    time: datetime
    result: str
    remark: str
    class Config:
        from_attributes = True


class YardPositionOut(BaseModel):
    id: int
    block: str
    bay: int
    row: int
    tier: int
    occupied: bool
    code: str
    container_no: Optional[str] = None
    class Config:
        from_attributes = True


class MoveRequest(BaseModel):
    container_no: str
    block: Optional[str] = None        # 指定目标区
    position_id: Optional[int] = None  # 或指定确切空位(优先)
    reason: str = ""


class MoveRecordOut(BaseModel):
    id: int
    container_id: int
    container_no: str = ""
    from_code: str
    to_code: str
    reason: str
    time: datetime
    class Config:
        from_attributes = True


CONTAINER_NO_RE = re.compile(r"^[A-Z]{4}\d{7}$")


def valid_container_no(no: str) -> bool:
    """ISO 6346 简单格式校验: 4位箱主代码 + 7位数字"""
    return bool(CONTAINER_NO_RE.match(no.upper()))
