from google import genai
from langchain_core.documents import Document
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def get_embedding(text: str) -> List[float]:
    """
    Transforme un texte en vecteur numérique via Gemini API.
    
    Args:
        text: texte à transformer
    
    Returns:
        Liste de floats représentant le vecteur
    """
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text
    )
    return response.embeddings[0].values

def get_embeddings_for_chunks(chunks: List[Document]) -> List[dict]:
    """
    Génère les embeddings pour une liste de chunks.
    
    Args:
        chunks: liste de Documents LangChain
    
    Returns:
        Liste de dicts avec texte, embedding et métadonnées
    """
    results = []
    for i, chunk in enumerate(chunks):
        print(f"Embedding chunk {i+1}/{len(chunks)}...")
        embedding = get_embedding(chunk.page_content)
        results.append({
            "text": chunk.page_content,
            "embedding": embedding,
            "metadata": chunk.metadata
        })
    return results