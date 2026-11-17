import os
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
app = FastAPI(title="Investment Intelligence Dashboard")
API_BASE_URL = os.getenv("API_BASE_URL", "").rstrip("/")
@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", encoding="utf-8") as f:
        return f.read()
@app.get("/dashboard-status")
async def dashboard_status():
    if not API_BASE_URL:
        return JSONResponse(status_code=503, content={"error": "API endpoint is not configured"})
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(API_BASE_URL + "/api/status")
            return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception:
        return JSONResponse(status_code=503, content={"error": "API service unavailable"})
