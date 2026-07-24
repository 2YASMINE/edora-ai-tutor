from chunker import chunk_text

text = """
L'intelligence artificielle est un domaine de l'informatique qui vise à créer des machines capables de simuler l'intelligence humaine.

Les principaux domaines de l'IA incluent l'apprentissage automatique, le traitement du langage naturel, la vision par ordinateur et la robotique.

La récursivité est une technique en programmation où une fonction s'appelle elle-même. Elle nécessite une condition d'arrêt pour éviter une boucle infinie.

Les arbres et les listes chaînées utilisent souvent la récursivité. Elle est très utilisée en algorithmique et en intelligence artificielle.
"""

chunks = chunk_text(
    text=text,
    source="test_cours.pdf",
    course_id=2,
    resource_id=1,
    chunk_size=200,
    chunk_overlap=30
)

print(f"Nombre de chunks : {len(chunks)}")
print("---")
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1} :")
    print(f"  Texte : {chunk.page_content[:80]}...")
    print(f"  Métadonnées : {chunk.metadata}")
    print()