import json
import os

from flask import Flask, render_template, request
from flask_sock import Sock
from simple_websocket import ConnectionClosed

from game import GameSession, MAX_QUESTION_LENGTH
from limits import GameLimiter


def send_and_close(ws, data: str) -> None:
    """Send a final message, then complete the close handshake before teardown."""
    ws.send(data)
    try:
        ws.close()
        ws.receive(timeout=1)
    except (ConnectionClosed, OSError):
        pass

app = Flask(__name__)
sock = Sock(app)
limiter = GameLimiter()


def client_ip() -> str:
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "unknown"


@app.route("/")
def index():
    return render_template("index.html")


@sock.route("/ws")
def ws(ws):
    if not limiter.allow(client_ip()):
        send_and_close(ws, json.dumps({"type": "error", "message": "limit reached: 3 games per day per IP"}))
        return

    session = GameSession()

    while True:
        raw = ws.receive()
        if raw is None:
            break
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            ws.send(json.dumps({"type": "error", "message": "invalid json"}))
            continue

        if msg.get("type") == "question":
            question = str(msg.get("question", ""))
            if not question or len(question) > MAX_QUESTION_LENGTH:
                ws.send(
                    json.dumps(
                        {
                            "type": "error",
                            "message": f"question must be 1-{MAX_QUESTION_LENGTH} characters",
                        }
                    )
                )
                continue
            try:
                result = session.ask(question)
            except NotImplementedError as exc:
                send_and_close(ws, json.dumps({"type": "error", "message": str(exc)}))
                return
            if result["type"] in ("success", "fail"):
                send_and_close(ws, json.dumps(result))
                return
            ws.send(json.dumps(result))
        elif msg.get("type") == "give_up":
            result = session.give_up()
            if result["type"] in ("success", "fail"):
                send_and_close(ws, json.dumps(result))
                return
            ws.send(json.dumps(result))
        else:
            ws.send(json.dumps({"type": "error", "message": "unknown type"}))
    ws.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
