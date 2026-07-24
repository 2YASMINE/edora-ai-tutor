from chunker import chunk_text
from embeddings import get_embeddings_for_chunks

text = """
L'intelligence artificielle est un domaine de l'informatique qui vise à créer des machines capables de simuler l'intelligence humaine.

La récursivité est une technique en programmation où une fonction s'appelle elle-même.
"""

# Chunking
chunks = chunk_text(
    text=text,
    source="test.pdf",
    course_id=2,
    resource_id=1,
    chunk_size=200,
    chunk_overlap=30
)

print(f"Nombre de chunks : {len(chunks)}")

# Embeddings
results = get_embeddings_for_chunks(chunks)

for i, r in enumerate(results):
    print(f"\nChunk {i+1} :")
    print(f"  Texte : {r['text'][:50]}...")
    print(f"  Taille vecteur : {len(r['embedding'])} dimensions")
    print(f"  Métadonnées : {r['metadata']}")