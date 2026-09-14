from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from ..database import get_db
from ..models import Container, Vessel, YardPosition, GateRecord, Appointment, ContainerStatus

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    in_yard = db.query(Container).filter(Container.status == ContainerStatus.IN_YARD.value).all()
    overdue = [c for c in in_yard if c.in_time and now > c.in_time + timedelta(days=c.free_days)]
    total_pos = db.query(func.count(YardPosition.id)).scalar()
    used_pos = db.query(func.count(YardPosition.id)).filter(YardPosition.occupied == True).scalar()  # noqa: E712
    today_in = db.query(func.count(GateRecord.id)).filter(
        GateRecord.direction == "IN", GateRecord.result == "OK",
        GateRecord.time >= now.replace(hour=0, minute=0, second=0)).scalar()
    today_out = db.query(func.count(GateRecord.id)).filter(
        GateRecord.direction == "OUT", GateRecord.result == "OK",
        GateRecord.time >= now.replace(hour=0, minute=0, second=0)).scalar()
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
