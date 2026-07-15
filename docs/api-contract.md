# Contrat API REST — Plugin Moodle ↔ Microservice IA

## Principes généraux

- Format d'échange : JSON uniquement (`Content-Type: application/json`)
- Authentification : header `X-API-Key` (clé partagée entre plugin et microservice, définie en variable d'environnement des deux côtés)
- Tous les timestamps au format ISO 8601 (`2026-07-15T14:30:00Z`)
- Codes HTTP standards : 200 (succès), 400 (requête invalide), 401 (clé API invalide), 404 (ressource introuvable), 500 (erreur serveur), 503 (LLM externe indisponible)

---

## `GET /health`

Vérifie que le microservice est disponible.

**Requête :** aucun corps.

**Réponse 200 OK :**
```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

---

## `POST /ask`

L'étudiant pose une question sur le cours en cours.

**Requête :**
```json
{
  "question": "Peux-tu m'expliquer la récursivité ?",
  "course_id": 42,
  "student_id": 17,
  "conversation_id": "conv_abc123"
}
```

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `question` | string | oui | Question posée par l'étudiant |
| `course_id` | int | oui | ID du cours Moodle, pour cibler la bonne collection ChromaDB |
| `student_id` | int | oui | ID Moodle de l'étudiant, pour l'historique |
| `conversation_id` | string | non | Identifiant de conversation en cours, pour garder le contexte multi-tours. Absent = nouvelle conversation |

**Réponse 200 OK :**
```json
{
  "answer": "La récursivité est une technique où une fonction s'appelle elle-même...",
  "conversation_id": "conv_abc123",
  "sources": [
    {"resource_name": "Chapitre 3 - Algorithmique.pdf", "chunk_excerpt": "..."}
  ],
  "found_in_course": true
}
```

| Champ | Description |
|---|---|
| `answer` | Réponse générée par le LLM |
| `conversation_id` | À réutiliser pour le prochain message de cette conversation |
| `sources` | Liste des chunks utilisés pour générer la réponse (traçabilité) |
| `found_in_course` | `false` si l'info n'était pas dans le cours (le microservice doit alors répondre honnêtement, pas halluciner) |

**Réponse 400 Bad Request** (champ obligatoire manquant) :
```json
{
  "error": "missing_field",
  "message": "Le champ 'question' est requis"
}
```

**Réponse 503 Service Unavailable** (Gemini API indisponible) :
```json
{
  "error": "llm_unavailable",
  "message": "Le service IA est temporairement indisponible, réessayez dans quelques instants"
}
```

---

## `POST /upload-resource`

Déclenché quand un enseignant upload une ressource sur Moodle. Lance l'extraction, le chunking et l'indexation dans ChromaDB.

**Requête :**
```json
{
  "course_id": 42,
  "resource_id": 205,
  "resource_type": "pdf",
  "file_url": "http://moodle:8080/pluginfile.php/.../chapitre3.pdf"
}
```

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `course_id` | int | oui | ID du cours concerné |
| `resource_id` | int | oui | ID Moodle de la ressource |
| `resource_type` | string | oui | `"pdf"` ou `"page"` |
| `file_url` | string | oui | URL Moodle pour récupérer le fichier |

**Réponse 200 OK :**
```json
{
  "status": "processing",
  "resource_id": 205,
  "chunks_created": null
}
```

Note : le traitement est asynchrone (extraction + embeddings peut prendre du temps), donc la réponse initiale confirme juste la prise en charge. `chunks_created` sera renseigné dans une future version avec un endpoint de suivi de statut (`GET /upload-resource/{resource_id}/status`), à définir en Phase 3.

**Réponse 404 Not Found** (fichier introuvable) :
```json
{
  "error": "file_not_found",
  "message": "Impossible de récupérer le fichier depuis Moodle"
}
```

---

## Historique des versions de ce contrat

| Date | Modification |
|---|---|
| 15 juillet 2026 | Version initiale — `/health`, `/ask`, `/upload-resource` |