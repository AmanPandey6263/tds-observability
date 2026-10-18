import json
import time
import uuid
from collections import deque, defaultdict
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

EMAIL = "24f3004942@ds.study.iitm.ac.in"
START = time.time()

REQUEST_COUNTS = defaultdict(int)  # (method, path, status) -> count
LOGS = deque(maxlen=1000)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def observe(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    path = request.url.path
    REQUEST_COUNTS[(request.method, path, response.status_code)] += 1
    entry = {
        "level": "INFO",
        "ts": datetime.now(timezone.utc).isoformat(),
        "path": path,
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
        "duration_ms": round(duration * 1000, 3),
    }
    LOGS.append(entry)
    print(json.dumps(entry), flush=True)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/work")
def work(n: int = Query(1, ge=0)):
    total = 0
    for i in range(n):
        total += i * i
    return {"email": EMAIL, "done": n}


@app.get("/healthz")
def healthz():
    return {"status": "ok", "uptime_s": max(time.time() - START, 0.0)}


@app.get("/metrics")
def metrics():
    lines = [
        "# HELP http_requests_total Total HTTP requests.",
        "# TYPE http_requests_total counter",
    ]
    for (method, path, status), count in REQUEST_COUNTS.items():
        lines.append(
            f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}'
        )
    if not REQUEST_COUNTS:
        lines.append("http_requests_total 0")
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.get("/logs/tail")
def logs_tail(limit: int = Query(50, ge=1, le=1000)):
    return list(LOGS)[-limit:]
