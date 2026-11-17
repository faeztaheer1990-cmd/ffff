import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import psycopg

DATABASE_URL=os.getenv("DATABASE_URL")
MT5_INGEST_TOKEN=os.getenv("MT5_INGEST_TOKEN")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
                with conn.cursor() as cur:
                    cur.execute("""CREATE TABLE IF NOT EXISTS market_watchlist (
                        symbol TEXT PRIMARY KEY, display_name TEXT NOT NULL,
                        enabled BOOLEAN NOT NULL DEFAULT TRUE)""")
                    cur.executemany("INSERT INTO market_watchlist(symbol,display_name) VALUES (%s,%s) ON CONFLICT (symbol) DO NOTHING",
                        [("XAUUSD","Gold / USD"),("NAS100","NASDAQ 100"),("EURUSD","EUR / USD")])
                    cur.execute("""CREATE TABLE IF NOT EXISTS mt5_ticks (
                        id BIGSERIAL PRIMARY KEY, symbol TEXT NOT NULL, bid DOUBLE PRECISION NOT NULL,
                        ask DOUBLE PRECISION NOT NULL, tick_time TIMESTAMPTZ NOT NULL,
                        received_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
                    cur.execute("CREATE INDEX IF NOT EXISTS mt5_ticks_symbol_time_idx ON mt5_ticks(symbol,tick_time DESC)")
                conn.commit()
        except Exception as exc: print(f"Database initialization warning: {type(exc).__name__}")
    yield

app=FastAPI(title="Investment Intelligence API",version="0.2.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

class TickIn(BaseModel):
    symbol:str=Field(min_length=1,max_length=32,pattern=r"^[A-Za-z0-9._-]+$")
    bid:float=Field(gt=0,allow_inf_nan=False)
    ask:float=Field(gt=0,allow_inf_nan=False)
    time:int=Field(gt=0)

@app.get("/health")
def health():
    db="not_configured"
    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL,connect_timeout=4) as conn:
                with conn.cursor() as cur: cur.execute("SELECT 1"); cur.fetchone()
            db="connected"
        except Exception: db="unavailable"
    return {"status":"ok","database":db,"time":datetime.now(timezone.utc).isoformat()}

@app.get("/api/status")
def status():
    return {"company":"Investment Intelligence Company","stage":"initial_setup","live_trading":False,
            "market_data":"read_only_pending","message":"MT5 read-only tick ingestion configured; no trading orders enabled."}

@app.get("/api/watchlist")
def watchlist():
    if not DATABASE_URL: return JSONResponse(status_code=503,content={"error":"Database is not configured"})
    try:
        with psycopg.connect(DATABASE_URL,connect_timeout=5) as conn:
            with conn.cursor() as cur: cur.execute("SELECT symbol,display_name,enabled FROM market_watchlist ORDER BY symbol"); rows=cur.fetchall()
        return {"items":[{"symbol":r[0],"name":r[1],"enabled":r[2]} for r in rows]}
    except Exception: return JSONResponse(status_code=503,content={"error":"Database unavailable"})

@app.post("/api/mt5/tick")
def receive_mt5_tick(tick:TickIn,authorization:str|None=Header(default=None)):
    if not MT5_INGEST_TOKEN or authorization!=f"Bearer {MT5_INGEST_TOKEN}": raise HTTPException(status_code=401,detail="Unauthorized")
    if not DATABASE_URL: raise HTTPException(status_code=503,detail="Database unavailable")
    try:
        tick_time=datetime.fromtimestamp(tick.time,tz=timezone.utc)
        with psycopg.connect(DATABASE_URL,connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO mt5_ticks(symbol,bid,ask,tick_time) VALUES (%s,%s,%s,%s)",(tick.symbol,tick.bid,tick.ask,tick_time))
            conn.commit()
        return {"accepted":True}
    except Exception as exc:
        print(f"MT5 tick storage warning: {type(exc).__name__}")
        raise HTTPException(status_code=503,detail="Could not store tick")

@app.get("/api/mt5/latest")
def latest_mt5_ticks():
    if not DATABASE_URL: raise HTTPException(status_code=503,detail="Database unavailable")
    with psycopg.connect(DATABASE_URL,connect_timeout=5) as conn:
        with conn.cursor() as cur:
            cur.execute("""SELECT DISTINCT ON (symbol) symbol,bid,ask,tick_time,received_at FROM mt5_ticks ORDER BY symbol,tick_time DESC""")
            rows=cur.fetchall()
    return {"items":[{"symbol":r[0],"bid":r[1],"ask":r[2],"tick_time":r[3].isoformat(),"received_at":r[4].isoformat()} for r in rows]}

@app.get("/")
def root(): return {"service":"Investment Intelligence API","docs":"/docs","health":"/health"}
