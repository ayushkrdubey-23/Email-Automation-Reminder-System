import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from src.api.routes import router


def create_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Email Automation & Reminder System API",
        description="REST API for scheduling and sending automated emails with reminders",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")

    # Serve static dashboard
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "static")
    static_dir = os.path.abspath(static_dir)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def dashboard():
        """Serve the dashboard HTML page."""
        return FileResponse(os.path.join(static_dir, "index.html"))

    return app


app = create_app()
