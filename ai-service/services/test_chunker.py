from chunker import chunk_text

texte_test = """
L'intelligence artificielle est un domaine de l'informatique.
Elle vise a creer des systemes capables d'effectuer des taches
qui necessitent normalement l'intelligence humaine.

Les principaux domaines de l'IA incluent l'apprentissage automatique,
le traitement du langage naturel et la vision par ordinateur.

La recursivite est une technique de programmation ou une fonction
s'appelle elle-meme. C'est un concept fondamental en informatique.

Les arbres et les listes chainées sont des structures de donnees
tres utilisees en programmation. Elles permettent d'organiser
les informations de maniere efficace.
"""

chunks = chunk_text(
    text=texte_test,
    source="test.pdf",
    course_id=2,
    resource_id=1
)

print(f"Nombre de chunks : {len(chunks)}")
for i, chunk in enumerate(chunks, 1):
    print(f"\nChunk {i} :")
    print(f"  Texte    : {chunk.page_content[:80]}...")
    print(f"  Metadata : {chunk.metadata}")