"""FastAPI backend for the React trading dashboard."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import portfolios, forward, prices, moby

app = FastAPI(
    title="Stock Planner Trading API",
    description="Read-only API for the React trading dashboard",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(portfolios.router)
app.include_router(forward.router)
app.include_router(prices.router)
app.include_router(moby.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
