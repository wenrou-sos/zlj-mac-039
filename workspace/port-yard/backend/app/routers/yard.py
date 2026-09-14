from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import YardPosition, Container, MoveRecord, ContainerStatus
from ..schemas import YardPositionOut, MoveRequest, MoveRecordOut

router = APIRouter(prefix="/api/yard", tags=["堆位"])


def to_out(p: YardPosition) -> dict:
    return {
        "id": p.id, "block": p.block, "bay": p.bay, "row": p.row, "tier": p.tier,
        "occupied": p.occupied, "code": p.code,
        "container_no": p.container.container_no if p.container else None,
    }


@router.get("/positions", response_model=List[YardPositionOut])
def list_positions(block: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(YardPosition)
    if block:
        q = q.filter(YardPosition.block == block.upper())
    return [to_out(p) for p in q.order_by(YardPosition.block, YardPosition.bay,
                                          YardPosition.row, YardPosition.tier).all()]


@router.get("/summary")
def yard_summary(db: Session = Depends(get_db)):
    """各区占用率"""
    rows = db.query(YardPosition).all()
    summary = {}
    for p in rows:
        s = summary.setdefault(p.block, {"block": p.block, "total": 0, "occupied": 0})
        s["total"] += 1
        s["occupied"] += 1 if p.occupied else 0
    for s in summary.values():
        s["rate"] = round(s["occupied"] / s["total"] * 100, 1) if s["total"] else 0
    return sorted(summary.values(), key=lambda x: x["block"])


def allocate_position(db: Session, prefer_block: Optional[str] = None) -> Optional[YardPosition]:
    """自动分配堆位: 优先指定区，按 区-排-列-层 顺序找第一个空位"""
    q = db.query(YardPosition).filter(YardPosition.occupied == False)  # noqa: E712
    if prefer_block:
        q = q.filter(YardPosition.block == prefer_block.upper())
    pos = q.order_by(YardPosition.block, YardPosition.bay,
                     YardPosition.row, YardPosition.tier).first()
    if not pos and prefer_block:  # 指定区满了则全场找
        pos = db.query(YardPosition).filter(YardPosition.occupied == False).order_by(
            YardPosition.block, YardPosition.bay, YardPosition.row, YardPosition.tier).first()
    return pos


@router.post("/allocate/{container_id}", response_model=YardPositionOut)
def manual_allocate(container_id: int, block: Optional[str] = None, db: Session = Depends(get_db)):
    c = db.get(Container, container_id)
    if not c:
        raise HTTPException(404, "集装箱不存在")
    if c.status == ContainerStatus.IN_YARD.value:
        raise HTTPException(400, "该箱已在场内，无需预分配")
    if c.position_id:
        raise HTTPException(400, f"已分配堆位 {c.position.code}")
    pos = allocate_position(db, block)
    if not pos:
        raise HTTPException(409, "堆场已满，无可用堆位")
    pos.occupied = True
    c.position_id = pos.id
    db.commit()
    db.refresh(pos)
    return to_out(pos)


@router.post("/release/{container_id}", response_model=YardPositionOut)
def release_allocation(container_id: int, db: Session = Depends(get_db)):
    """释放预分配堆位: 仅未进场箱可释放，避免堆位被永久占用"""
    c = db.get(Container, container_id)
    if not c:
        raise HTTPException(404, "集装箱不存在")
    if not c.position_id:
        raise HTTPException(400, "该箱没有预分配堆位")
    if c.status == ContainerStatus.IN_YARD.value:
        raise HTTPException(400, "该箱已在场内，请通过移箱或出闸释放堆位")
    pos = c.position
    pos.occupied = False
    c.position_id = None
    db.commit()
    db.refresh(pos)
    return to_out(pos)


@router.post("/move", response_model=MoveRecordOut)
def move_container(req: MoveRequest, db: Session = Depends(get_db)):
    """移箱: 指定确切空位 / 指定区自动找位 / 全场自动找位，全程留痕"""
    no = req.container_no.upper()
    c = db.query(Container).filter(Container.container_no == no).first()
    if not c:
        raise HTTPException(404, "箱号不存在")
    if c.status != ContainerStatus.IN_YARD.value or not c.position:
        raise HTTPException(400, "该箱不在场内或无堆位，无法移箱")
    old = c.position

    if req.position_id:  # 指定确切空位
        new = db.get(YardPosition, req.position_id)
        if not new:
            raise HTTPException(404, "目标堆位不存在")
        if new.occupied:
            raise HTTPException(409, f"目标堆位 {new.code} 已被占用")
    else:  # 指定区或全场自动找位
        new = allocate_position(db, req.block)
        if not new:
            raise HTTPException(409, "目标区域无可用空位" if req.block else "堆场已满，无可用堆位")

    old.occupied = False
    new.occupied = True
    c.position_id = new.id
    rec = MoveRecord(container_id=c.id, from_code=old.code, to_code=new.code,
                     reason=req.reason)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {**{col.name: getattr(rec, col.name) for col in MoveRecord.__table__.columns},
            "container_no": no}


@router.get("/moves", response_model=List[MoveRecordOut])
def list_moves(limit: int = 50, db: Session = Depends(get_db)):
    """移箱记录: 占用格归属可追溯"""
    recs = db.query(MoveRecord).order_by(MoveRecord.time.desc()).limit(limit).all()
    return [
        {**{col.name: getattr(r, col.name) for col in MoveRecord.__table__.columns},
         "container_no": r.container.container_no if r.container else ""}
        for r in recs
    ]
