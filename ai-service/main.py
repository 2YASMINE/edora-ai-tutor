import logging
from fastapi import FastAPI
from routers import chat, resources
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

print("MOODLE_INTERNAL_URL =", os.getenv("MOODLE_INTERNAL_URL"))

# Configuration du logging pour voir tous les messages INFO
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s: %(message)s"
)

app = FastAPI(
    title="Edora Tutor AI - Microservice",
    description="Microservice IA pour l'assistant de tutorat Moodle",
    version="1.0.0"
)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

app.include_router(chat.router)
app.include_router(resources.router)