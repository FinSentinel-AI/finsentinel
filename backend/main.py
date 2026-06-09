import os
import json
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from agent.orchestrator import create_orchestrator

load_dotenv()

app = FastAPI(title="FinSentinel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_NAME = "finsentinel"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/healthz")
async def health():
    return {"status": "ok", "timestamp": _ts()}


@app.websocket("/ws/investigate")
async def investigate_ws(websocket: WebSocket):
    await websocket.accept()
    session_service = InMemorySessionService()
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        query = payload.get("query", "Investigate the last 24 hours for fraud and AML violations.")
        session_id = payload.get("session_id", f"session_{datetime.now().timestamp()}")
        user_id = payload.get("user_id", "analyst_1")

        await websocket.send_json({
            "type": "status",
            "message": "Investigation started — deploying 5 specialist agents...",
            "timestamp": _ts(),
        })

        agent = create_orchestrator()

        # ADK 2.x: create_session is async
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=session_service,
            auto_create_session=True,
        )

        user_message = Content(role="user", parts=[Part(text=query)])

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=user_message,
        ):
            if event.is_final_response():
                final_text = ""
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text"):
                            final_text += part.text
                await websocket.send_json({
                    "type": "final",
                    "agent": "finsentinel_orchestrator",
                    "content": final_text,
                    "timestamp": _ts(),
                })
            elif hasattr(event, "content") and event.content:
                author = getattr(event, "author", "agent")
                for part in (event.content.parts or []):
                    if hasattr(part, "text") and part.text:
                        await websocket.send_json({
                            "type": "agent_step",
                            "agent": author,
                            "content": part.text,
                            "timestamp": _ts(),
                        })

        await websocket.send_json({"type": "done", "timestamp": _ts()})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import traceback
        await websocket.send_json({"type": "error", "message": str(e), "trace": traceback.format_exc()[-500:]})


class InvestigateRequest(BaseModel):
    query: str
    session_id: str | None = None


@app.post("/api/investigate")
async def investigate_http(req: InvestigateRequest):
    """HTTP fallback — non-streaming."""
    session_id = req.session_id or f"session_{datetime.now().timestamp()}"
    user_id = "analyst_1"
    session_service = InMemorySessionService()

    agent = create_orchestrator()
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
        auto_create_session=True,
    )

    user_message = Content(role="user", parts=[Part(text=req.query)])
    result_parts = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_message
    ):
        if event.is_final_response() and event.content:
            for part in (event.content.parts or []):
                if hasattr(part, "text"):
                    result_parts.append(part.text)

    return {"result": "\n".join(result_parts), "session_id": session_id}


# Serve React frontend in production
frontend_dist = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
