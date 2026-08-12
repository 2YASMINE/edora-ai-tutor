from pydantic import BaseModel
from typing import Optional, List

# ── Message d'historique ──
class ConversationMessage(BaseModel):
    role: str   # "user" ou "assistant"
    content: str

# Request /ask
class AskRequest(BaseModel):
    question: str
    course_id: int
    student_id: int
    conversation_id: Optional[str] = None
    conversation_history: Optional[List[ConversationMessage]] = []  # ← ajout Phase 7

# Response /ask
class SourceChunk(BaseModel):
    resource_name: str
    chunk_excerpt: str

class AskResponse(BaseModel):
    answer: str
    conversation_id: str
    sources: List[SourceChunk]
    found_in_course: bool
    chunks_used: int   
    follow_up_questions: Optional[List[str]] = []
    
    class AskResponse(BaseModel):
     answer: str
    conversation_id: str
    sources: List[SourceChunk]
    found_in_course: bool
    chunks_used: int   
    follow_up_questions: Optional[List[str]] = []
    is_quiz_json: Optional[bool] = False  # ← ajouter cette ligne

# Request /upload-resource
class UploadResourceRequest(BaseModel):
    course_id: int
    resource_id: int
    resource_type: str
    file_url: str

# Response /upload-resource
class UploadResourceResponse(BaseModel):
    status: str
    resource_id: int
    chunks_created: Optional[int] = None