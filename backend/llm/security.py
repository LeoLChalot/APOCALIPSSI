import re
import unicodedata
from typing import Set

class PromptInjectionException(Exception):
    """
    Exception personnalisée levée lorsqu'une tentative d'injection de prompt 
    ou de détournement (jailbreak) est détectée dans les entrées utilisateur.
    """
    def __init__(self, message: str, detected_pattern: str = None):
        super().__init__(message)
        self.detected_pattern = detected_pattern


class PromptSanitizer:
    """
    Couche de sécurité logicielle (Sanitization Layer) conçue pour intercepter
    les attaques par injection de prompt directes (Jailbreaks) et indirectes (PDF piégés).
    Fonctionne de manière déterministe en 4 étapes de filtrage.
    """

    def __init__(self):
        # 3. BLACKLIST HEURISTIQUE
        # Mots-clés de jailbreak connus (normalisés en minuscules et sans accents)
        self.forbidden_keywords: Set[str] = {
            "ignore previous", "ignore les instructions", "ignore toutes les",
            "ignore la consigne", "ignore le system", "tu es maintenant", 
            "tu dois maintenant", "you are now", "act as a", "forget instructions",
            "forget previous", "system prompt", "consigne systeme", "mode developpeur",
            "developer mode", "override instructions", "bypass security",
            "code secret", "mot de passe", "prompt injection", "ne genere pas",
            "do not generate", "ignore everything", "instruction importante"
        }

        # 2. REGEX ANTI-ÉVASION
        # Détection de motifs structurels complexes et d'évasion XML
        self.malicious_patterns = [
            # Détection des impératifs d'évasion d'instructions
            re.compile(r"(?:ignore|oublie|forget|override|bypass)\s+(?:toutes?\s+|les?\s+|mes?\s+|tes?\s+|your?\s+|all?\s+)?(?:instructions?|consignes?|prompts?|rules?)", re.IGNORECASE),
            # Détection des tentatives de vol d'identité d'agent ("Tu es maintenant...")
            re.compile(r"(?:tu\s+es\s+maintenant|you\s+are\s+now|act\s+as\s+a)\s+[\w\s]{2,30}(?:assistant|pirate|developpeur|dev|root|admin)", re.IGNORECASE),
            # Détection d'injection de directives alternatives déguisées
            re.compile(r"\[(?:note\s+importante|attention|consigne|system)\]", re.IGNORECASE),
            # Détection d'attaques de fin de balise d'ancrage XML (ex: </DATA>, </text>)
            re.compile(r"</\s*(?:data|text|course|source|context|prompt|xml)\s*>", re.IGNORECASE),
            # Tentative d'ouverture de balises de configuration système
            re.compile(r"<\s*system_override\s*>", re.IGNORECASE)
        ]

    def _normalize_text(self, text: str) -> str:
        """
        1. NORMALISATION UNICODE
        Neutralise l'obfuscation : retire les accents, passe en minuscules, 
        supprime les caractères de masquage (Zero-Width Space, homoglyphes partiels).
        """
        if not text:
            return ""
        # Décomposition Unicode (NFD) pour séparer les lettres de leurs accents
        text_normalized = unicodedata.normalize('NFD', text)
        # Filtrage des caractères diacritiques (accents)
        text_clean = "".join([c for c in text_normalized if unicodedata.category(c) != 'Mn'])
        # Conversion en minuscules et nettoyage des espaces invisibles/doubles
        return " ".join(text_clean.lower().split())

    def sanitize(self, raw_text: str) -> str:
        """
        Analyse et sécurise le texte (saisie libre ou contenu PDF) avant l'envoi au LLM local.
        
        Args:
            raw_text (str): Le contenu textuel brut à valider.
            
        Returns:
            str: Le texte échappé et sécurisé.
            
        Raises:
            PromptInjectionException: Si un motif malveillant est détecté.
        """
        if not raw_text or not raw_text.strip():
            return ""

        # ACTION 1 : Normalisation Unicode
        normalized_text = self._normalize_text(raw_text)

        # ACTION 2 : Regex Anti-Évasion
        # On vérifie à la fois sur le texte brut (pour les balises) et normalisé (pour le sémantique)
        for pattern in self.malicious_patterns:
            match = pattern.search(raw_text) or pattern.search(normalized_text)
            if match:
                raise PromptInjectionException(
                    message="Tentative d'injection de prompt détectée via expression régulière (Anti-Évasion).",
                    detected_pattern=match.group(0)
                )

        # ACTION 3 : Blacklist Heuristique
        for keyword in self.forbidden_keywords:
            if keyword in normalized_text:
                raise PromptInjectionException(
                    message="Mot-clé d'injection de prompt interdit détecté (Blacklist).",
                    detected_pattern=keyword
                )

        # ACTION 4 : Échappement XML
        # Remplacement préventif des chevrons restants pour sanitariser l'entrée face au System Prompt
        sanitized_text = raw_text.replace("<", "&lt;").replace(">", "&gt;")

        return sanitized_text
