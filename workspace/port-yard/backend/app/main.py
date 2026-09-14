from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, run_migrations
from .seed import seed
from .routers import vessels, containers, yard, gate, appointments, dashboard

Base.metadata.create_all(bind=engine)
run_migrations()
seed()

app = FastAPI(title="港口集装箱堆场管理系统", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (vessels.router, containers.router, yard.router,
          gate.router, appointments.router, dashboard.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}
