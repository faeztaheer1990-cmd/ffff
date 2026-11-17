import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
                with conn.cursor() as cur:
                    cur.execute("""CREATE TABLE IF NOT EXISTS market_watchlist (
                        symbol TEXT PRIMARY KEY, display_name TEXT NOT NULL,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE)""")
                    cur.executemany(
                        "INSERT INTO market_watchlist(symbol, display_name) VALUES (%s, %s) ON CONFLICT (symbol) DO NOTHING",
                        [("XAUUSD", "Gold / USD"), ("NAS100", "NASDAQ 100"), ("EURUSD", "EUR / USD")])
                conn.commit()
        except Exception as exc:
            print(f"Database initialization warning: {type(exc).__name__}")
    yield

app = FastAPI(title="Investment Intelligence API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    db = "not_configured"
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=4) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            db = "connected"
        except Exception:
            db = "unavailable"
    return {"status": "ok", "database": db, "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/status")
def status():
    return {"company": "Investment Intelligence Company", "stage": "initial_setup",
            "live_trading": False, "market_data": "not_connected",
            "message": "No live prices or trading orders are enabled."}

@app.get("/api/watchlist")
def watchlist():
    if not DATABASE_URL:
        return JSONResponse(status_code=503, content={"error": "Database is not configured"})
    try:
        with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT symbol, display_name, enabled FROM market_watchlist ORDER BY symbol")
                rows = cur.fetchall()
        return {"items": [{"symbol": r[0], "name": r[1], "enabled": r[2]} for r in rows]}
    except Exception:
        return JSONResponse(status_code=503, content={"error": "Database unavailable"})

@app.get("/")
def root():
    return {"service": "Investment Intelligence API", "docs": "/docs", "health": "/health"}
