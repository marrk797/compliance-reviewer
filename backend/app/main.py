"""FastAPI application entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_setup import configure_logging
from app.routers import auth as auth_router
from app.routers import reports as reports_router
from app.routers import uploads as uploads_router

configure_logging()

app = FastAPI(
    title="Compliance Reviewer API",
    version="0.1.0",
    description=(
        "Assists human compliance reviewers. Not a substitute for legal advice. "
        "Uploaded documents are private to the uploading user and may be deleted "
        "after a report is generated, depending on the privacy mode configuration."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/disclaimer", tags=["meta"])
def disclaimer() -> dict[str, str]:
    return {
        "notice": (
            "This tool assists human compliance reviewers. It does not provide "
            "legal advice and is not a substitute for qualified counsel. Do not "
            "upload personal or confidential data unless you are authorized to "
            "do so. Source files are deleted after report generation when the "
            "privacy mode is enabled."
        ),
        "delete_source_files_after_processing": str(
            settings.delete_source_files_after_processing
        ).lower(),
    }


app.include_router(auth_router.router)
app.include_router(uploads_router.router)
app.include_router(reports_router.router)
