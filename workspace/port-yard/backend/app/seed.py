"""本地模拟数据: 堆场、船期、集装箱、预约、闸口记录"""
from datetime import datetime, timedelta
import random

from .database import SessionLocal, Base, engine
from .models import Vessel, YardPosition, Container, Appointment, GateRecord, ContainerStatus

random.seed(42)


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if db.query(Vessel).count() > 0:
        db.close()
        return

    now = datetime.utcnow()

    # 1. 堆场: A/B/C 三个区, 每区 6排 x 4列 x 3层 = 72 位
    positions = []
    for block in "ABC":
        for bay in range(1, 7):
            for row in range(1, 5):
                for tier in range(1, 4):
                    positions.append(YardPosition(block=block, bay=bay, row=row, tier=tier))
    db.add_all(positions)
    db.flush()

    # 2. 船期
    vessels = [
        Vessel(vessel_name="COSCO SHIPPING UNIVERSE", voyage="CSU208E",
               eta=now - timedelta(days=2), etd=now + timedelta(days=1), status="BERTHED"),
        Vessel(vessel_name="EVER GOLDEN", voyage="EG105W",
               eta=now + timedelta(days=1), etd=now + timedelta(days=3), status="SCHEDULED"),
        Vessel(vessel_name="MSC GULSUN", voyage="MG332N",
               eta=now + timedelta(days=4), etd=now + timedelta(days=6), status="SCHEDULED"),
        Vessel(vessel_name="ONE APUS", voyage="OA091S",
               eta=now - timedelta(days=10), etd=now - timedelta(days=8), status="DEPARTED"),
    ]
    db.add_all(vessels)
    db.flush()

    # 3. 集装箱: 部分在场(含超期), 部分已预约, 部分已出场
    owners = ["MSKU", "TCLU", "CSNU", "GESU", "OOCU", "HLCU", "TEMU", "FCIU"]
    consignees = ["华远物流", "中集货运", "远洋贸易", "顺达供应链", "恒通仓储"]
    containers = []
    for i in range(40):
        no = f"{random.choice(owners)}{random.randint(1000000, 9999999)}"
        c = Container(
            container_no=no,
            size=random.choice(["20", "40", "40", "45"]),
            ctype=random.choice(["GP", "GP", "HC", "RF"]),
            vessel_id=random.choice(vessels).id,
            weight_t=round(random.uniform(5, 28), 1),
            consignee=random.choice(consignees),
            free_days=random.choice([5, 7, 10]),
        )
        containers.append(c)
    db.add_all(containers)
    db.flush()

    free_positions = [p for p in positions]
    random.shuffle(free_positions)

    # 25 个在场箱 (其中约 8 个超期)
    for c in containers[:25]:
        pos = free_positions.pop()
        pos.occupied = True
        c.position_id = pos.id
        c.status = ContainerStatus.IN_YARD.value
        overdue = containers.index(c) < 8
        days_ago = random.randint(8, 20) if overdue else random.randint(0, 4)
        c.in_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        db.add(GateRecord(container_id=c.id, direction="IN",
                          truck_no=f"沪A{random.randint(10000, 99999)}",
                          driver=random.choice(["王强", "李伟", "张军", "刘洋"]),
                          gate=random.choice(["G1", "G2"]), time=c.in_time,
                          result="OK", remark=f"分配堆位 {pos.code}"))
    containers[2].has_hold = True  # 一个扣箱用于演示提箱拦截

    # 8 个已出场
    for c in containers[25:33]:
        c.status = ContainerStatus.OUT.value
        c.in_time = now - timedelta(days=random.randint(6, 12))
        c.out_time = c.in_time + timedelta(days=random.randint(2, 5))
        db.add(GateRecord(container_id=c.id, direction="IN", truck_no="沪B33821",
                          driver="赵磊", gate="G1", time=c.in_time, result="OK"))
        db.add(GateRecord(container_id=c.id, direction="OUT", truck_no="沪B33821",
                          driver="赵磊", gate="G1", time=c.out_time, result="OK",
                          remark="提箱单 PK202609001"))

    # 7 个已预约未进场 + 对应预约单 (含 2 个已过预约时段, 1 个即将到场)
    offsets = [-8, -3, 0.5, 3, 8, 24, 40]   # 小时; 负数=已过期
    for c, hours in zip(containers[33:], offsets):
        db.add(Appointment(
            container_no=c.container_no, vessel_id=c.vessel_id,
            planned_time=now + timedelta(hours=hours),
            tolerance_hours=random.choice([1, 2, 3]),
            truck_no=f"沪C{random.randint(10000, 99999)}",
        ))

    db.commit()
    db.close()
    print("✅ 模拟数据已生成: 3个堆区/216个堆位, 4条船期, 40个集装箱, 7条预约")


if __name__ == "__main__":
    seed()
