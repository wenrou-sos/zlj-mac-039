from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from ..database import get_db
from ..models import Container, Vessel, YardPosition, ContainerStatus
from ..schemas import ContainerIn, ContainerOut, ContainerUpdate, valid_container_no

router = APIRouter(prefix="/api/containers", tags=["集装箱"])


def to_out(c: Container) -> dict:
    now = datetime.utcnow()
    free_days = c.free_days_effective
    days = (now - c.in_time).days if c.in_time and c.status == ContainerStatus.IN_YARD.value else None
    overdue = bool(c.in_time and c.status == ContainerStatus.IN_YARD.value
                   and now > c.in_time + timedelta(days=free_days))
    return {
        "id": c.id, "container_no": c.container_no,
        "size": c.size or "", "ctype": c.ctype or "",
        "status": c.status, "vessel_id": c.vessel_id, "position_id": c.position_id,
        "position_code": c.position.code if c.position else None,
        "vessel_name": c.vessel.vessel_name if c.vessel else None,
        "weight_t": c.weight_t, "consignee": c.consignee or "", "free_days": free_days,
        "in_time": c.in_time, "out_time": c.out_time, "has_hold": c.has_hold,
        "overdue": overdue, "days_in_yard": days,
    }


@router.get("", response_model=List[ContainerOut])
def list_containers(status: Optional[str] = None, q: Optional[str] = None,
                    db: Session = Depends(get_db)):
    query = db.query(Container)
    if status:
        query = query.filter(Container.status == status)
    if q:
        query = query.filter(Container.container_no.contains(q.upper()))
    return [to_out(c) for c in query.order_by(Container.id.desc()).all()]


@router.get("/overdue", response_model=List[ContainerOut])
def overdue_containers(db: Session = Depends(get_db)):
    """超期箱提醒: 在场且超过免堆存天数"""
    now = datetime.utcnow()
    containers = db.query(Container).filter(Container.status == ContainerStatus.IN_YARD.value).all()
    return [to_out(c) for c in containers
            if c.in_time and now > c.in_time + timedelta(days=c.free_days_effective)]


@router.post("", response_model=ContainerOut)
def create_container(data: ContainerIn, db: Session = Depends(get_db)):
    no = data.container_no.upper()
    if not valid_container_no(no):
        raise HTTPException(400, "箱号格式错误，应为4位字母+7位数字 (ISO 6346)")
    if db.query(Container).filter(Container.container_no == no).first():
        raise HTTPException(409, "箱号已存在")
    if data.vessel_id and not db.get(Vessel, data.vessel_id):
        raise HTTPException(404, "船期不存在")
    c = Container(**{**data.model_dump(), "container_no": no})
    db.add(c)
    db.commit()
    db.refresh(c)
    return to_out(c)


@router.get("/{container_id}", response_model=ContainerOut)
def get_container(container_id: int, db: Session = Depends(get_db)):
    c = db.get(Container, container_id)
    if not c:
        raise HTTPException(404, "集装箱不存在")
    return to_out(c)


@router.patch("/{container_id}", response_model=ContainerOut)
def update_container(container_id: int, data: ContainerUpdate, db: Session = Depends(get_db)):
    """修改箱档案: 尺寸/箱型/货主/免堆天数/关联船期, 已预约/在场/已出场均可改。
    箱号与进出场时间不可改; 超期标记、看板超期数、超期清单均按新免堆天数实时重算。"""
    c = db.get(Container, container_id)
    if not c:
        raise HTTPException(404, "集装箱不存在")
    fields = data.model_dump(exclude_unset=True)
    if "vessel_id" in fields and fields["vessel_id"] is not None:
        if not db.get(Vessel, fields["vessel_id"]):
            raise HTTPException(404, "船期不存在")
    for k, v in fields.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return to_out(c)


@router.patch("/{container_id}/hold", response_model=ContainerOut)
def toggle_hold(container_id: int, hold: bool = Query(...), db: Session = Depends(get_db)):
    c = db.get(Container, container_id)
    if not c:
        raise HTTPException(404, "集装箱不存在")
    c.has_hold = hold
    db.commit()
    db.refresh(c)
    return to_out(c)
