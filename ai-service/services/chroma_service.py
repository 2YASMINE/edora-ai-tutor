"""
Service ChromaDB — stockage et recherche des vecteurs du cours.
Une collection par cours identifiee par course_id.
"""

import chromadb
import os
import logging

logger = logging.getLogger(__name__)

# Dossier persistant pour ChromaDB
CHROMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "chroma_db"
)

# Client ChromaDB persistant
_client = None


def get_client() -> chromadb.PersistentClient:
    """Retourne le client ChromaDB (singleton)."""
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
        logger.info(f"ChromaDB initialise : {CHROMA_PATH}")
    return _client


def get_or_create_collection(course_id: int):
    """
    Retourne la collection d'un cours.
    La cree si elle n'existe pas encore.
    Nom de collection : course_{course_id}
    """
    client = get_client()
    collection_name = f"course_{course_id}"

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}  # distance cosinus pour la similarite semantique
    )

    logger.info(f"Collection '{collection_name}' : {collection.count()} chunks existants")
    return collection


def store_chunks(course_id: int, embedded_chunks: list) -> dict:
    """
    Stocke les chunks et leurs embeddings dans ChromaDB.

    Args:
        course_id: ID du cours Moodle
        embedded_chunks: liste de dicts {text, embedding, metadata}
                         (sortie de get_embeddings_for_chunks)

    Returns:
        {success, chunks_stored, collection_name, error}
    """
    if not embedded_chunks:
        return {
            "success": False,
            "chunks_stored": 0,
            "collection_name": None,
            "error": "Aucun chunk a stocker"
        }

    try:
        collection = get_or_create_collection(course_id)
        collection_name = f"course_{course_id}"

        # Preparer les donnees pour ChromaDB
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(embedded_chunks):
            resource_id = chunk["metadata"].get("resource_id", 0)
            chunk_id = f"course_{course_id}_resource_{resource_id}_chunk_{i}"

            ids.append(chunk_id)
            embeddings.append(chunk["embedding"])
            documents.append(chunk["text"])
            metadatas.append({
                "course_id": str(course_id),
                "resource_id": str(resource_id),
                "source": chunk["metadata"].get("source", "unknown"),
            })

        # Insertion dans ChromaDB (upsert = insert ou update si existe deja)
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        total = collection.count()
        logger.info(f"Chunks stockes : {len(ids)} | Total collection : {total}")

        return {
            "success": True,
            "chunks_stored": len(ids),
            "collection_name": collection_name,
            "error": None
        }

    except Exception as e:
        logger.error(f"Erreur ChromaDB : {str(e)}")
        return {
            "success": False,
            "chunks_stored": 0,
            "collection_name": None,
            "error": str(e)
        }


def search_similar_chunks(course_id: int, query_embedding: list, n_results: int = 3) -> list:
    """
    Recherche les chunks les plus similaires a un embedding de requete.

    Args:
        course_id: ID du cours
        query_embedding: vecteur de la question (3072 dimensions)
        n_results: nombre de resultats a retourner

    Returns:
        Liste de dicts {text, metadata, distance}
    """
    try:
        collection = get_or_create_collection(course_id)

        if collection.count() == 0:
            logger.warning(f"Collection course_{course_id} est vide")
            return []

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, collection.count())
        )

        chunks = []
        for i in range(len(results["documents"][0])):
            chunks.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })

        return chunks

    except Exception as e:
        logger.error(f"Erreur recherche ChromaDB : {str(e)}")
        return []


def get_collection_info(course_id: int) -> dict:
    """Retourne les infos d'une collection (nombre de chunks, etc.)."""
    try:
        collection = get_or_create_collection(course_id)
        return {
            "collection_name": f"course_{course_id}",
            "chunk_count": collection.count(),
            "exists": True
        }
    except Exception as e:
        return {
            "collection_name": f"course_{course_id}",
            "chunk_count": 0,
            "exists": False,
            "error": str(e)
        }


def delete_course_collection(course_id: int) -> bool:
    """Supprime la collection d'un cours (utile pour re-indexer)."""
    try:
        client = get_client()
        client.delete_collection(f"course_{course_id}")
        logger.info(f"Collection course_{course_id} supprimee")
        return True
    except Exception as e:
        logger.error(f"Erreur suppression collection : {str(e)}")
        return False