import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from chunker import chunk_text
from embeddings import get_embeddings_for_chunks
from chroma_service import store_chunks, search_similar_chunks, get_collection_info

# Texte de test
texte = """
L'intelligence artificielle est un domaine de l'informatique qui vise
a creer des systemes capables d'apprendre et de raisonner comme les humains.

La recursivite est une technique ou une fonction s'appelle elle-meme.
Elle est tres utilisee pour resoudre des problemes complexes.

Les reseaux de neurones sont des modeles inspires du cerveau humain.
Ils sont utilises pour la reconnaissance d'images et le traitement du langage.
"""

print("=== TEST PIPELINE COMPLET ===\n")

# Etape 1 : Chunking
print("1. Chunking...")
chunks = chunk_text(texte, source="cours_ia.pdf", course_id=2, resource_id=1)
print(f"   {len(chunks)} chunks crees\n")

# Etape 2 : Embeddings
print("2. Generation des embeddings...")
embedded = get_embeddings_for_chunks(chunks)
print(f"   {len(embedded)} embeddings generes ({len(embedded[0]['embedding'])} dimensions)\n")

# Etape 3 : Stockage ChromaDB
print("3. Stockage dans ChromaDB...")
result = store_chunks(course_id=2, embedded_chunks=embedded)
print(f"   Succes : {result['success']}")
print(f"   Chunks stockes : {result['chunks_stored']}")
print(f"   Collection : {result['collection_name']}\n")

# Etape 4 : Recherche
print("4. Test de recherche semantique...")
from embeddings import get_embedding
query = "Comment fonctionne la recursion en programmation ?"
print(f"   Question : '{query}'")
query_embedding = get_embedding(query)
results = search_similar_chunks(course_id=2, query_embedding=query_embedding, n_results=2)
print(f"   {len(results)} chunks trouves :")
for i, r in enumerate(results, 1):
    print(f"   Chunk {i} (distance: {r['distance']:.4f}) : {r['text'][:80]}...")

# Infos collection
print("\n5. Infos collection :")
info = get_collection_info(course_id=2)
print(f"   Collection : {info['collection_name']}")
print(f"   Chunks total : {info['chunk_count']}")

print("\n=== PIPELINE RAG VALIDE ===")