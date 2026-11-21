"""FastAPI application factory: wires settings, database, routers and the UI."""
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import Settings, get_settings
from backend.database import Base, make_engine, make_session_factory
from backend.exceptions import register_exception_handlers
from backend.routers import auth, coupons, orders, restaurants
from backend.seed import seed_database


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        Base.metadata.create_all(engine)
        if settings.seed_on_startup:
            with session_factory() as session:
                seed_database(session, settings.password_iterations)
        yield
        engine.dispose()

    app = FastAPI(
        title="FoodDash API",
        description="A food delivery platform: restaurants, menus, carts, coupons and orders.",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    register_exception_handlers(app)

    @app.get("/api/health", tags=["system"])
    def health():
        return {"status": "ok", "service": "fooddash"}

    for module in (auth, restaurants, coupons, orders):
        app.include_router(module.router)

    frontend = settings.frontend_dir
    if frontend.exists():
        app.mount("/static", StaticFiles(directory=frontend), name="static")

        @app.get("/", include_in_schema=False)
        def index():
            return FileResponse(frontend / "index.html")

    return app


app = create_app()
