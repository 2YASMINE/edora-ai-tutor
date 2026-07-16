from fastapi import FastAPI
from routers import chat, resources

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