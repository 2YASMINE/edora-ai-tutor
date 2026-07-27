from chunker import chunk_text
from embeddings import get_embeddings_for_chunks

texte_test = """
L'intelligence artificielle est un domaine de l'informatique.
Elle vise a creer des systemes capables d'effectuer des taches
qui necessitent normalement l'intelligence humaine.

La recursivite est une technique de programmation ou une fonction
s'appelle elle-meme.
"""

chunks = chunk_text(
    text=texte_test,
    source="test.pdf",
    course_id=2,
    resource_id=1
)

print(f"Chunks crees : {len(chunks)}")

results = get_embeddings_for_chunks(chunks)

print(f"Embeddings generes : {len(results)}")
for i, r in enumerate(results, 1):
    print(f"\nChunk {i} :")
    print(f"  Texte     : {r['text'][:60]}...")
    print(f"  Dimensions: {len(r['embedding'])}")
    print(f"  Metadata  : {r['metadata']}")