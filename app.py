import asyncio
import importlib
import json
import os

import tslog
from quart import Quart, render_template, websocket

from game import GameSession, MAX_QUESTION_LENGTH
from limits import GameLimiter

app = Quart(__name__)
limiter = GameLimiter(path=os.environ.get("LIMITS_DB"))

_disconnect_types = []
for _mod, _names in (
    ("quart.wrappers.base", ("ClientDisconnectedError", "ConnectionClosed")),
    ("quart.ws", ("ConnectionClosed",)),
):
    try:
        _m = importlib.import_module(_mod)
    except ImportError:
        continue
    _disconnect_types += [getattr(_m, n) for n in _names if hasattr(_m, n)]
if not _disconnect_types:
    import websockets.exceptions

    _disconnect_types.append(websockets.exceptions.ConnectionClosed)
DISCONNECT_ERRORS = tuple(_disconnect_types)


def client_ip() -> str:
    cf = websocket.headers.get("CF-Connecting-IP", "")
    if cf:
        return cf.strip()
    xff = websocket.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    client = websocket.scope.get("client")
    if client:
        return client[0]
    return "unknown"


def limit_message() -> str:
    hours = max(limiter.window_seconds // 3600, 1)
    return f"daily limit reached"


@app.route("/")
async def index():
    return await render_template("index.html")


@app.websocket("/ws")
async def ws_handler():
    ip = client_ip()

    session = await asyncio.to_thread(GameSession)
    tslog.use(session.log)

    allowed = False
    while True:
        try:
            raw = await websocket.receive()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"type": "error", "message": "invalid json"}))
                continue

            if not allowed and not await asyncio.to_thread(limiter.allow, ip):
                await websocket.send(json.dumps({"type": "error", "message": limit_message()}))
                await websocket.close(1000)
                return

            allowed = True

            if msg.get("type") == "question":
                question = str(msg.get("question", ""))
                if not question or len(question) > MAX_QUESTION_LENGTH:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "error",
                                "message": f"question must be 1-{MAX_QUESTION_LENGTH} characters",
                            }
                        )
                    )
                    continue
                try:
                    result = await asyncio.to_thread(session.ask, question)
                except NotImplementedError as exc:
                    await websocket.send(json.dumps({"type": "error", "message": str(exc)}))
                    await websocket.close(1000)
                    return
                if result["type"] in ("success", "fail"):
                    result["limits"] = await asyncio.to_thread(limiter.status, ip)
                    await websocket.send(json.dumps(result))
                    await websocket.close(1000)
                    return
                await websocket.send(json.dumps(result))
            elif msg.get("type") in ("daily-mode", "endless-mode"):
                await websocket.send(json.dumps(session.set_mode(msg["type"])))
            elif msg.get("type") == "give_up":
                try:
                    result = await asyncio.to_thread(session.give_up)
                except NotImplementedError as exc:
                    await websocket.send(json.dumps({"type": "error", "message": str(exc)}))
                    await websocket.close(1000)
                    return
                result["limits"] = await asyncio.to_thread(limiter.status, ip)
                await websocket.send(json.dumps(result))
                await websocket.close(1000)
                return
            else:
                await websocket.send(json.dumps({"type": "error", "message": "unknown type"}))
        except DISCONNECT_ERRORS:
            break


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info")
