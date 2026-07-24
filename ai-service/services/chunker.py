from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List

def chunk_text(
    text: str,
    source: str = "unknown",
    course_id: int = 0,
    resource_id: int = 0,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Document]:
    """
    Découpe un texte en chunks intelligents avec métadonnées.
    
    Args:
        text: texte à découper
        source: nom du fichier source
        course_id: ID du cours Moodle
        resource_id: ID de la ressource Moodle
        chunk_size: taille de chaque chunk en caractères
        chunk_overlap: chevauchement entre chunks
    
    Returns:
        Liste de Documents LangChain avec métadonnées
    """
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = splitter.create_documents(
        texts=[text],
        metadatas=[{
            "source": source,
            "course_id": course_id,
            "resource_id": resource_id
        }]
    )

    return chunks