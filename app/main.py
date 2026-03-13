from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router
from app.api.routes.progress import router as progress_router


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""
    application = FastAPI(
        title="Document Analyzer API",
        version="0.1.0",
        description="API para analizar documentos visualmente con Ollama.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    application.include_router(analysis_router)
    application.include_router(progress_router)

    return application


app = create_app()
