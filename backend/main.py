import os
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
APP_NAME = "finsentinel"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"FinSentinel starting — model={MODEL}")
    yield


app = FastAPI(title="FinSentinel API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/healthz")
async def health():
    return {"status": "ok", "model": MODEL, "timestamp": _ts()}


@app.websocket("/ws/investigate")
async def investigate_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        query = payload.get("query", "Investigate the last 24 hours for fraud and AML violations.")

        await websocket.send_json({
            "type": "status",
            "message": f"Investigation started — deploying 5 specialist agents ({MODEL})...",
            "timestamp": _ts(),
        })

        from backend.pipeline import run_pipeline

        async def emit(event: dict):
            await websocket.send_json(event)

        await run_pipeline(query=query, on_event=emit)
        await websocket.send_json({"type": "done", "timestamp": _ts()})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "trace": traceback.format_exc()[-1200:],
            })
        except Exception:
            pass


class InvestigateRequest(BaseModel):
    query: str
    session_id: str | None = None


@app.post("/api/investigate")
async def investigate_http(req: InvestigateRequest):
    from backend.pipeline import run_pipeline

    results: list[dict] = []

    async def collect(event: dict):
        results.append(event)

    await run_pipeline(query=req.query, on_event=collect)
    final = next((r for r in reversed(results) if r.get("type") == "final"), None)
    return {
        "result": final.get("content", "") if final else "",
        "events": results,
    }


# Serve React frontend in production
frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
