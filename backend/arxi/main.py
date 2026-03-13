from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from arxi.auth.router import router as auth_router
from arxi.config import settings
from arxi.events import event_bus
from arxi.modules.compliance.router import router as audit_router
from arxi.modules.intake.router import router as intake_router
from arxi.modules.drug.router import router as drug_router
from arxi.modules.patient.router import router as patient_router
from arxi.modules.prescriber.router import router as prescriber_router
from arxi.ws import ws_events


@asynccontextmanager
async def lifespan(app: FastAPI):
    await event_bus.connect(settings.redis_url)
    yield
    await event_bus.disconnect()


app = FastAPI(title="Pharmagent", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.include_router(auth_router)
app.include_router(intake_router)
app.include_router(audit_router)
app.include_router(patient_router)
app.include_router(drug_router)
app.include_router(prescriber_router)

# WebSocket route (no router prefix — direct path)
app.websocket("/ws/events")(ws_events)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pharmagent"}
