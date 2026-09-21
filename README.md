# 🎓 Edora AI Tutor — Moodle Block Plugin

> Projet de stage d'été 2026 — Edora LMS (Québec)  
> Binôme : **Yasmine** + **Islem Troudi**

Plugin Moodle de tutorat intelligent basé sur une architecture RAG (*Retrieval-Augmented Generation*). Le chatbot **Edo** répond aux questions des étudiants à partir du contenu indexé de leur cours, avec détection de niveau, gamification XP et génération d'images pédagogiques.

---

## Stack technique

| Couche | Technologie |
|---|---|
| LMS | Moodle 4.4 (Bitnami Docker) |
| Plugin | PHP — `block_tutor_ai` |
| Microservice IA | FastAPI + Uvicorn (port 8000) |
| Base vectorielle | ChromaDB (persistant) |
| LLM | Gemini 3.5 Flash (Google API) |
| Génération image | Gemini 2.5 Flash Image |
| Embeddings | gemini-embedding-2 (3072 dim) |
| Base de données | MariaDB |
| Transcription vidéo | Whisper + yt-dlp + ffmpeg |

---

## Lancer le projet

### 1 — Variables d'environnement

Créer un fichier `.env` à la racine :

```env
MOODLE_WS_TOKEN=votre_token_webservice
MOODLE_BASE_URL=http://localhost:8082
GEMINI_API_KEY=votre_cle_api_gemini
GEMINI_TIMEOUT=30
```

### 2 — Démarrer Moodle

```bash
docker compose up -d
```

### 3 — Démarrer le microservice IA

```bash
cd ai-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4 — Vérifier

```bash
curl http://localhost:8000/health
# → {"status": "ok", "version": "1.0.0"}
```

---

## Ce qui est réalisé

| Phase | Description | Statut |
|---|---|---|
| 0 | Docker + Moodle installé | ✅ |
| 1 | Squelette plugin Moodle | ✅ |
| 2 | Squelette FastAPI + Hello World | ✅ |
| 3 | Extraction PDF/DOCX/PPTX/TXT + pages Moodle | ✅ |
| 4 | Chunking LangChain + Embeddings Gemini + ChromaDB | ✅ |
| 5 | Prompt RAG + Persona Edo + Appel Gemini + Logging | ✅ |
| 6 | Interface chat UI + styles | ✅ |
| 7 | Historique conversation (MySQL + affichage) | ✅ |
| 8 | Prompt engineering avancé, détection niveau étudiant, quiz / résumé / exemples, gamification XP, dashboards prof & admin, génération d'images, export PDF session | ✅ |

---

## Structure du repo

```
edora-ai-tutor/
├── moodle-plugin/blocks/tutor_ai/   # Plugin PHP Moodle
├── ai-service/                      # Microservice FastAPI
│   ├── routers/                     # Endpoints (chat, quiz, image...)
│   ├── services/                    # RAG pipeline (extract, chunk, embed, chroma)
│   └── chroma_db/                   # Base vectorielle persistante
└── docs/                            # Documentation
    └── Admin_Guide.html             # Guide administrateur complet
```

---

## Équipe

| Membre | Rôles principaux |
|---|---|
| **Yasmine** | Chunking, Embeddings, Prompt engineering, Appel Gemini, Endpoints quiz/résumé/exemples, Observer PHP, UI chat |
| **Islem Troudi** | Extraction documents, ChromaDB, Gestion erreurs/logs, Détection niveau étudiant, Dashboards |

---

## Documentation

👉 Voir [`docs/Admin_Guide.html`](docs/Admin_Guide.html) pour le guide administrateur complet :
architecture détaillée, endpoints API, schéma base de données, troubleshooting.

---

> Repo de travail : [islemTroudi/edora-ai-tutor](https://github.com/islemTroudi/edora-ai-tutor)  
> Repo officiel Edora : [edoralms/edoralms-moodle-block_ai_tutor_03](https://github.com/edoralms/edoralms-moodle-block_ai_tutor_03)
