from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import invoices, reports, anomalies, dashboard, audit

app = FastAPI(title="E-Invoice Compliance Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(anomalies.router, prefix="/anomalies", tags=["anomalies"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(audit.router, prefix="/audit-logs", tags=["audit"])


@app.get("/health")
async def health():
    return {"status": "ok"}
