import re


class PromptInjectionException(Exception):
    """Exception levée en cas de tentative d'injection de prompt."""

    pass


class PromptSanitizer:
    """Classe responsable de la détection et neutralisation des injections de prompts."""

    def __init__(self):
        # Détecte toute fermeture de balise structurelle critique ou tentative d'injection
        self.malicious_patterns = [
            # XML/HTML structure escape detection
            re.compile(r"</\s*(?:data|text|course|source|context|prompt|xml)\s*>", re.IGNORECASE),
            re.compile(r"<\s*system_override\s*>", re.IGNORECASE),
            # End of document delimiter markers
            re.compile(
                r"[-=_#*]{3,}\s*END OF (?:DOCUMENT|TEXT|COURSE|SOURCE|CONTEXT|PROMPT|DATA)\s*[-=_#*]{3,}",
                re.IGNORECASE,
            ),
            # Bracketed administrative override markers
            re.compile(
                r"\[\s*(?:ADMIN|SYSTEM|USER|SUPERVISOR|ROOT|MODERATOR)\s+OVERRIDE\s*\]",
                re.IGNORECASE,
            ),
            # Common instruction overrides and jailbreaks
            re.compile(
                r"(?:ignore|override|suspend|bypass)\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules|directives|formatting|constraints|system)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:instructions|rules|directives|formatting|constraints)\s+(?:are\s+)?(?:suspended|ignored|overridden|invalidated|bypassed)",
                re.IGNORECASE,
            ),
            re.compile(r"mandatory\s+system\s+update", re.IGNORECASE),
        ]

    def sanitize(self, raw_text: str) -> str:
        if not raw_text:
            return ""

        # 1. Validation Fail-Fast
        for pattern in self.malicious_patterns:
            if pattern.search(raw_text):
                raise PromptInjectionException(
                    "Le texte ou le document soumis a été bloqué pour des raisons de sécurité car il contient "
                    "des instructions suspectes (comme des consignes demandant d'ignorer les règles, des délimiteurs "
                    "de document inhabituels ou des commandes système). Ces éléments ressemblent à une tentative de "
                    "manipulation de l'intelligence artificielle (injection de prompt). Veuillez nettoyer votre "
                    "texte avant de le soumettre à nouveau."
                )

        # 2. Neutralisation (Échappement des chevrons)
        sanitized_text = raw_text.replace("<", "&lt;").replace(">", "&gt;")
        return sanitized_text
