from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

    return app


app = create_app()
