from chunker import chunk_text

text = "La recursivite est une technique en programmation. Une fonction recursive est une fonction qui s appelle elle meme. Elle necessite une condition arret pour eviter boucle infinie. Les arbres et listes chainees utilisent souvent la recursivite."

chunks = chunk_text(text, chunk_size=10, overlap=2)
for c in chunks:
    print(f"Chunk {c['index']} ({c['word_count']} mots): {c['text']}")