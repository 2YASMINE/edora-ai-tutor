from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from typing import List
import re


def chunk_text(
    text: str,
    source: str = "unknown",
    course_id: int = 0,
    resource_id: int = 0,
    chunk_size: int = 800,
    chunk_overlap: int = 50,
    is_video: bool = False
) -> List[Document]:
    """
    Découpe un texte en chunks intelligents avec métadonnées.
    Pour les vidéos, respecte les timestamps [MM:SS] comme séparateurs
    naturels afin que chaque chunk conserve sa référence temporelle.

    Args:
        text (str)        : Texte à découper.
        source (str)      : Nom du fichier source.
        course_id (int)   : ID du cours Moodle.
        resource_id (int) : ID de la ressource Moodle.
        chunk_size (int)  : Taille maximale d'un chunk en caractères.
        chunk_overlap (int): Chevauchement entre chunks consécutifs.
        is_video (bool)   : True si le texte provient d'une transcription vidéo
                            (active le chunking par timestamps).

    Returns:
        List[Document]: Liste de Documents LangChain avec métadonnées.
                        Chaque document contient source, course_id, resource_id,
                        et pour les vidéos : timestamp de début du chunk.

    Example:
        >>> chunks = chunk_text(text, source="cours.pdf", course_id=1, resource_id=2)
        >>> chunks = chunk_text(text, source="cours.mp4", course_id=1, resource_id=2, is_video=True)
    """
    if not text or not text.strip():
        return []

    if is_video:
        return _chunk_video(text, source, course_id, resource_id, chunk_size)

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


def _chunk_video(
    text: str,
    source: str,
    course_id: int,
    resource_id: int,
    chunk_size: int = 800
) -> List[Document]:
    """
    Découpe une transcription vidéo en chunks en regroupant les segments
    par timestamp [MM:SS] jusqu'à atteindre chunk_size caractères.
    Chaque chunk conserve le timestamp du premier segment qu'il contient.

    Args:
        text (str)        : Transcription vidéo avec timestamps [MM:SS].
        source (str)      : Nom du fichier vidéo source.
        course_id (int)   : ID du cours Moodle.
        resource_id (int) : ID de la ressource Moodle.
        chunk_size (int)  : Taille maximale d'un chunk en caractères.

    Returns:
        List[Document]: Chunks avec métadonnée "timestamp" du début de chaque chunk.

    Example output (metadata):
        {"source": "cours.mp4", "course_id": 1, "resource_id": 2, "timestamp": "[00:00]"}
    """
    # Sépare chaque ligne [MM:SS] texte
    pattern = re.compile(r'(\[\d{2}:\d{2}\])\s*(.*)')
    segments = []
    for line in text.strip().split("\n"):
        match = pattern.match(line)
        if match:
            segments.append({
                "timestamp": match.group(1),
                "text": match.group(2).strip()
            })

    if not segments:
        return []

    chunks = []
    current_texts = []
    current_timestamp = segments[0]["timestamp"]
    current_length = 0

    for segment in segments:
        segment_text = f"{segment['timestamp']} {segment['text']}"
        if current_length + len(segment_text) > chunk_size and current_texts:
            # Sauvegarde le chunk courant
            chunks.append(Document(
                page_content="\n".join(current_texts),
                metadata={
                    "source": source,
                    "course_id": course_id,
                    "resource_id": resource_id,
                    "timestamp": current_timestamp
                }
            ))
            # Nouveau chunk
            current_texts = [segment_text]
            current_timestamp = segment["timestamp"]
            current_length = len(segment_text)
        else:
            current_texts.append(segment_text)
            current_length += len(segment_text)

    # Dernier chunk
    if current_texts:
        chunks.append(Document(
            page_content="\n".join(current_texts),
            metadata={
                "source": source,
                "course_id": course_id,
                "resource_id": resource_id,
                "timestamp": current_timestamp
            }
        ))

    return chunks