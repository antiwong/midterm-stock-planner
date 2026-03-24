"""FastAPI backend for the React trading dashboard."""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import init_auth_db, validate_session
from .routers import (
    auth_routes,
    portfolios,
    forward,
    prices,
    moby,
    alerts,
    commentary,
    comparison,
    earnings,
    monitoring,
    particles,
    recommendations,
    runs,
    sentiment,
    settings,
    signals,
    similar_days,
    ticker,
    watchlists,
)

# Paths that don't require authentication
PUBLIC_PATHS = {"/api/health", "/api/auth/login", "/api/auth/me"}

app = FastAPI(
    title="Stock Planner Trading API",
    description="Authenticated API for the React trading dashboard",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["*"],
    allow_credentials=True,
)


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")

        # Allow public paths and OPTIONS (CORS preflight)
        if path in PUBLIC_PATHS or request.method == "OPTIONS":
            return await call_next(request)

        # Allow logout even with expired session
        if path == "/api/auth/logout":
            return await call_next(request)

        # Check session cookie
        token = request.cookies.get("sp_session")
        user = validate_session(token) if token else None
        if not user:
            return Response(
                content='{"detail":"Not authenticated"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)


app.add_middleware(AuthMiddleware)

# Initialize auth DB on startup
init_auth_db()

# Auth
app.include_router(auth_routes.router)

# Core trading
app.include_router(portfolios.router)
app.include_router(forward.router)
app.include_router(commentary.router)
app.include_router(prices.router)
app.include_router(moby.router)

# Analysis
app.include_router(sentiment.router)
app.include_router(comparison.router)
app.include_router(earnings.router)
app.include_router(monitoring.router)
app.include_router(signals.router)
app.include_router(recommendations.router)
app.include_router(watchlists.router)

# Ticker detail
app.include_router(ticker.router)
app.include_router(particles.router)
app.include_router(similar_days.router)

# System
app.include_router(alerts.router)
app.include_router(runs.router)
app.include_router(settings.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
