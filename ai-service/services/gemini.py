# TODO: Phase 5 - Intégration API Gemini
# Ce fichier contiendra la logique d'appel à gemini-3.5-flash

class GeminiService:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def generate_response(self, question: str, context: str) -> str:
        # TODO: implémenter l'appel Gemini
        pass