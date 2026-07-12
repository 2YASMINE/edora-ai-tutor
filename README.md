<div align="center">

# 🎓 Edora AI Tutor

### *Un tuteur qui connaît ses limites — et les respecte.*

**Un assistant IA pédagogique qui ne répond qu'avec ce que le cours contient.**  
Jamais plus. Jamais moins. Jamais inventé.

![Status](https://img.shields.io/badge/status-en%20d%C3%A9veloppement-orange)
![Python](https://img.shields.io/badge/Python-FastAPI-3776AB?logo=python&logoColor=white)
![PHP](https://img.shields.io/badge/PHP-Moodle%20Plugin-777BB4?logo=php&logoColor=white)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-6C4FF6)
![Gemini](https://img.shields.io/badge/LLM-Gemini%20Flash-4285F4?logo=googlegemini&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)

</div>

---

## 💡 L'idée en une phrase

> Les étudiants apprennent souvent seuls, le soir, coincés sur un concept — et l'enseignant n'est pas toujours là pour répondre. **Edora AI Tutor** comble ce vide, mais avec une règle stricte : il ne parle **que** de ce que le cours enseigne.

Pas de réponse Google déguisée. Pas d'improvisation. Si l'info n'est pas dans le cours, il le dit — clairement, honnêtement.

---

## 🧠 Comment ça pense

1. 👩‍🎓 **L'étudiant pose une question** dans le chat du cours
2. 📘 Le contexte du **cours Moodle** est identifié
3. 🔌 Le **Plugin PHP** capture la question (interface + auth + identification du cours) et l'envoie via REST API
4. 🐍 Le **Microservice Python (FastAPI)** prend le relais
5. ✂️ **Chunking** → 🧬 **Embeddings** → 🔍 **Recherche vectorielle**
6. 🗂️ Les chunks pertinents sont retrouvés dans **ChromaDB** (la mémoire du cours)
7. ✨ **Gemini Flash** génère une réponse, strictement à partir du contexte retrouvé
8. 💬 La réponse est renvoyée au plugin puis **affichée à l'étudiant**

> **La règle d'or du système :** aucune génération de réponse sans passage préalable par la recherche dans le cours. Le LLM n'a jamais le champ libre.

---

## 📁 Anatomie du repo

| Dossier | Rôle |
|---|---|
| 🔌 `moodle-plugin/` | Interface, auth, pont vers Moodle (PHP) |
| 🐍 `ai-service/` | Cerveau RAG : chunking, embeddings, LLM (Python) |
| 📚 `docs/` | Décisions techniques, architecture, specs |
| 🐳 `docker-compose.yml` | Un `docker compose up` et tout tourne |

## 🛠️ Sous le capot

| Brique | Techno | Rôle |
|---|---|---|
| 🖥️ Interface | PHP · Moodle Plugin API · JS | Chat intégré nativement dans le cours |
| 🧩 Microservice IA | Python · FastAPI | Orchestration du pipeline RAG |
| 🗂️ Mémoire vectorielle | ChromaDB | Stockage & recherche sémantique des chunks |
| 🧾 Historique | MySQL | Conversations persistantes par étudiant |
| 🤖 Génération | Gemini Flash | Réponses ancrées dans le contexte retrouvé |
| 📦 Environnement | Docker · Docker Compose | Setup reproductible en une commande |

---

## ✨ Ce que le tuteur saura faire

- [ ] 💬 Répondre aux questions sur le contenu exact du cours
- [ ] 🔄 Reformuler un concept difficile de plusieurs façons
- [ ] 📝 Générer des questions de révision sur mesure
- [ ] 🎯 Donner des exemples concrets, ancrés dans le cours
- [ ] 🧵 Garder le fil d'une conversation dans le temps
- [ ] 🚫 Dire "je ne trouve pas ça dans le cours" plutôt que d'inventer

---

## 👩‍💻 L'équipe derrière le projet

<div align="center">

| 👤 | Rôle | Terrain de jeu |
|---|---|---|
| **Islem Troudi** | 🏗️ Lead Plugin & Infra | Moodle, PHP, Docker, API REST, déploiement , prompting |
| **Yasmine Briki** | 🧠 Lead AI & RAG Pipeline | Extraction, chunking, embeddings, ChromaDB, UI interface |

*Stage — Edora LMS · 2026*

</div>

---

## 🚦 Où on en est

🟠 **Phase 0 — Setup de l'environnement** *(en cours)*

Le détail des phases, des décisions techniques et de l'avancement est dans [`docs/`](./docs).

---

<div align="center">

*Construit avec 🩵 par deux stagiaires qui refusent qu'une IA invente la réponse.*

</div>
