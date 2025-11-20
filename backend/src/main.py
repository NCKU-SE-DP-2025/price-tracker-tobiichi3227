import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.config import settings
from src.news.router import router as news_router
from src.news.scheduler import NewsScheduler
from src.price.router import router as price_router


def create_app() -> FastAPI:
    app = FastAPI(title="Price Tracker API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api/v1/users")
    app.include_router(news_router, prefix="/api/v1/news")
    app.include_router(price_router, prefix="/api/v1/prices")

    news_scheduler = NewsScheduler()

    @app.on_event("startup")
    async def startup_event():
        logging.info("Starting up the application...")
        news_scheduler.start()

    @app.on_event("shutdown")
    async def shutdown_event():
        logging.info("Shutting down the application...")
        news_scheduler.shutdown()

    return app


app = create_app()
