# Décisions techniques

## LLM Provider — 12 juillet 2026
**Décision :** Gemini Flash 3.5 (API Google AI Studio)
**Participants :** Islem, Yasmine
**Raison principale :** Tier gratuit généreux adapté à un projet de stage sans budget, vitesse d'inférence élevée pour de bonnes performances en démo.
**Alternative écartée et pourquoi :** Claude API — plus strict sur le respect des consignes (ne pas halluciner hors contexte), mais tier gratuit trop limité pour du développement itératif sans budget.
**Note pour la suite :** Le microservice sera architecturé avec une couche d'abstraction sur le LLM, pour permettre de changer de fournisseur plus tard sans réécrire le code métier.