import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, resources
from routers.flashcards import router as flashcards_router
from dotenv import load_dotenv
from db.migrations import run_migrations
from routers.export import router as export_router
from routers.xp import router as xp_router 

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s: %(message)s"
)

app = FastAPI(
    title="Edora Tutor AI - Microservice",
    description="Microservice IA pour l'assistant de tutorat Moodle",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8082",
        "http://127.0.0.1:8082",
        "http://host.docker.internal:8082",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    run_migrations()

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

app.include_router(chat.router)
app.include_router(resources.router)
app.include_router(flashcards_router)
app.include_router(export_router)
app.include_router(xp_router)