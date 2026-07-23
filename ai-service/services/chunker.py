from typing import List

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[dict]:
    """
    Découpe un texte en chunks avec overlap.
    
    Args:
        text: texte à découper
        chunk_size: nombre de mots par chunk
        overlap: nombre de mots en commun entre chunks
    
    Returns:
        Liste de chunks avec index et texte
    """
    if not text or not text.strip():
        return []

    # Découper en mots
    words = text.split()
    chunks = []
    index = 0
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = ' '.join(chunk_words)

        chunks.append({
            'index': index,
            'text': chunk_text,
            'word_count': len(chunk_words),
            'start_word': start,
            'end_word': min(end, len(words))
        })

        index += 1
        start += chunk_size - overlap

    return chunks