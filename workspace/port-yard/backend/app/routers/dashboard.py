from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import os

from ..database import get_db
from ..models import Container, Vessel, YardPosition, GateRecord, Appointment, ContainerStatus

router = APIRouter(prefix="/api/dashboard", tags=["看板"])

# “今日”统计口径使用的本地时区, 默认中国标准时间(无夏令时); 部署其他港口可设 YARD_TZ
LOCAL_TZ = ZoneInfo(os.getenv("YARD_TZ", "Asia/Shanghai"))


def local_day_start_utc() -> datetime:
    """本地今日零点换算为 UTC naive 时间, 与库中 UTC 时间戳同口径比较"""
    midnight_local = datetime.now(LOCAL_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight_local.astimezone(timezone.utc).replace(tzinfo=None)


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    in_yard = db.query(Container).filter(Container.status == ContainerStatus.IN_YARD.value).all()
    overdue = [c for c in in_yard if c.in_time and now > c.in_time + timedelta(days=c.free_days_effective)]
    total_pos = db.query(func.count(YardPosition.id)).scalar()
    used_pos = db.query(func.count(YardPosition.id)).filter(YardPosition.occupied == True).scalar()  # noqa: E712
    day_start = local_day_start_utc()
    today_in = db.query(func.count(GateRecord.id)).filter(
        GateRecord.direction == "IN", GateRecord.result == "OK",
        GateRecord.time >= day_start).scalar()
    today_out = db.query(func.count(GateRecord.id)).filter(
        GateRecord.direction == "OUT", GateRecord.result == "OK",
        GateRecord.time >= day_start).scalar()
    pending_appts = db.query(Appointment).filter(Appointment.status == "PENDING").all()
    expired_appts = [a for a in pending_appts
                     if now > a.planned_time + timedelta(hours=a.tolerance_hours)]
    return {
        "in_yard": len(in_yard),
        "overdue": len(overdue),
        "booked": db.query(func.count(Container.id)).filter(
            Container.status == ContainerStatus.BOOKED.value).scalar(),
        "vessels_active": db.query(func.count(Vessel.id)).filter(Vessel.status != "DEPARTED").scalar(),
        "yard_total": total_pos,
        "yard_used": used_pos,
        "yard_rate": round(used_pos / total_pos * 100, 1) if total_pos else 0,
        "today_in": today_in,
        "today_out": today_out,
        "pending_appointments": len(pending_appts) - len(expired_appts),
        "expired_appointments": len(expired_appts),
    }
