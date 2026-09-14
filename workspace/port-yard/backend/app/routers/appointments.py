from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from ..database import get_db
from ..models import Appointment, Container, Vessel
from ..schemas import AppointmentIn, AppointmentOut, RescheduleIn, valid_container_no

router = APIRouter(prefix="/api/appointments", tags=["预约"])


def window(a: Appointment):
    """到场时段 = 计划时间 ± 容差"""
    start = a.planned_time - timedelta(hours=a.tolerance_hours)
    end = a.planned_time + timedelta(hours=a.tolerance_hours)
    return start, end


def is_expired(a: Appointment, now: Optional[datetime] = None) -> bool:
    if a.status != "PENDING":
        return False
    now = now or datetime.utcnow()
    return now > window(a)[1]


def to_out(a: Appointment) -> dict:
    start, end = window(a)
    return {
        "id": a.id, "container_no": a.container_no, "vessel_id": a.vessel_id,
        "planned_time": a.planned_time, "tolerance_hours": a.tolerance_hours,
        "truck_no": a.truck_no, "status": a.status, "created_at": a.created_at,
        "window_start": start, "window_end": end, "is_expired": is_expired(a),
    }


@router.get("", response_model=List[AppointmentOut])
def list_appointments(status: str = None, expired: bool = None,
                      db: Session = Depends(get_db)):
    q = db.query(Appointment)
    if status:
        q = q.filter(Appointment.status == status)
    items = q.order_by(Appointment.planned_time).all()
    if expired is not None:
        items = [a for a in items if is_expired(a) == expired]
    return [to_out(a) for a in items]


@router.post("", response_model=AppointmentOut)
def create_appointment(data: AppointmentIn, db: Session = Depends(get_db)):
    no = data.container_no.upper()
    if not valid_container_no(no):
        raise HTTPException(400, "箱号格式错误")
    if data.tolerance_hours < 1 or data.tolerance_hours > 24:
        raise HTTPException(400, "容差应在 1~24 小时之间")
    # 同一箱存在未完成预约时不允许重复占用时段
    dup = db.query(Appointment).filter(
        Appointment.container_no == no, Appointment.status == "PENDING").first()
    if dup:
        raise HTTPException(409, "该箱已有待进场预约，请先改期或取消")
    if data.planned_time + timedelta(hours=data.tolerance_hours) <= datetime.utcnow():
        raise HTTPException(400, "预约时段已过期，请选择未来的计划时间")
    if data.vessel_id and not db.get(Vessel, data.vessel_id):
        raise HTTPException(404, "船期不存在")
    # 若箱档案不存在则自动建档(预约即登记)
    c = db.query(Container).filter(Container.container_no == no).first()
    if not c:
        c = Container(container_no=no, vessel_id=data.vessel_id)
        db.add(c)
    else:
        if c.status == "IN_YARD":
            raise HTTPException(400, "该箱已在场内，无需预约进场")
        if data.vessel_id and not c.vessel_id:
            c.vessel_id = data.vessel_id
    appt = Appointment(**{**data.model_dump(), "container_no": no})
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return to_out(appt)


@router.patch("/{appt_id}/reschedule", response_model=AppointmentOut)
def reschedule_appointment(appt_id: int, data: RescheduleIn, db: Session = Depends(get_db)):
    """改期: 原时段立即释放，占用新时段"""
    a = db.get(Appointment, appt_id)
    if not a:
        raise HTTPException(404, "预约不存在")
    if a.status != "PENDING":
        raise HTTPException(400, "仅待进场预约可改期")
    tol = data.tolerance_hours if data.tolerance_hours is not None else a.tolerance_hours
    if tol < 1 or tol > 24:
        raise HTTPException(400, "容差应在 1~24 小时之间")
    if data.planned_time + timedelta(hours=tol) <= datetime.utcnow():
        raise HTTPException(400, "新时段已过期，请选择未来的计划时间")
    a.planned_time = data.planned_time
    a.tolerance_hours = tol
    db.commit()
    db.refresh(a)
    return to_out(a)


@router.patch("/{appt_id}/cancel", response_model=AppointmentOut)
def cancel_appointment(appt_id: int, db: Session = Depends(get_db)):
    a = db.get(Appointment, appt_id)
    if not a:
        raise HTTPException(404, "预约不存在")
    if a.status != "PENDING":
        raise HTTPException(400, "仅待进场预约可取消")
    a.status = "CANCELLED"
    db.commit()
    db.refresh(a)
    return to_out(a)
