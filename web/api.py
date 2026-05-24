from fastapi import FastAPI, HTTPException
from app.analytics.schemas import EventIn
from app.analytics.raw_store import write_raw_event

app = FastAPI(title="clickhouse-events-analytics")

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.post("/events")
def collect_event(event: EventIn) -> dict[str, str]:
    try:
        write_raw_event(event.model_dump())
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"event_store_error: {exc}") from exc