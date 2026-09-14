from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Vessel
from ..schemas import VesselIn, VesselOut

router = APIRouter(prefix="/api/vessels", tags=["船期"])


@router.get("", response_model=List[VesselOut])
def list_vessels(db: Session = Depends(get_db)):
    return db.query(Vessel).order_by(Vessel.eta).all()


@router.post("", response_model=VesselOut)
def create_vessel(data: VesselIn, db: Session = Depends(get_db)):
    if data.etd <= data.eta:
        raise HTTPException(400, "离港时间必须晚于到港时间")
    v = Vessel(**data.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.patch("/{vessel_id}/status", response_model=VesselOut)
def update_status(vessel_id: int, status: str, db: Session = Depends(get_db)):
    v = db.get(Vessel, vessel_id)
    if not v:
        raise HTTPException(404, "船期不存在")
    if status not in ("SCHEDULED", "BERTHED", "DEPARTED"):
        raise HTTPException(400, "非法状态")
    v.status = status
    db.commit()
    db.refresh(v)
    return v
