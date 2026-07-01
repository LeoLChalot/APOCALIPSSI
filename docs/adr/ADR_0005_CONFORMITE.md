
# Architectural Decision Record (ADR)

## ADR-002 : Choix stratégique d'une couche d'assainissement déterministe locale contre les injections de prompt

* **Statut :** Accepté
* **Date :** 2026-07-01
* **Contexte :** Perturbation J3 (Sécurité et conformité des LLM)
* **Auteurs :** Équipe EduTutor IA

---

## 1. Contexte

Lors du Jour 3 du sprint, l'équipe a identifié une vulnérabilité non-fonctionnelle critique : les **injections de prompt** (Prompt Injections). Notre application ingère des documents textuels libres ainsi que des fichiers PDF fournis par des étudiants et des enseignants pour générer des QCM. Des utilisateurs malveillants peuvent y dissimuler des instructions pirates (ex: attaques par contournement de contexte avec des balises de rupture comme `</DATA>`) afin de détourner le comportement du modèle de langage local (Ollama).

Cette faille peut permettre à un attaquant de forcer l'IA à ignorer sa tâche pédagogique, à restituer le prompt système d'origine, ou à générer du contenu inapproprié. 

Nous devons déployer un mécanisme de protection robuste (Feature F5.1) pour intercepter ces attaques avant qu'elles ne compromettent l'infrastructure, tout en respectant les contraintes de performance (latence ≤ 15s) arbitrées lors du Jour 2 (ADR-001).

---

## 2. Options Envisagées

Trois approches d'ingénierie ont été évaluées pour sécuriser les flux d'entrées :

* **Option A : Solution de garde par LLM synchrone (LLM Guardrail)** Utiliser un modèle d'IA local très léger (ex: Llama 3.2 3B) ou une API distante dédiée uniquement à l'analyse de l'input utilisateur avant de solliciter le LLM principal. Le petit modèle détermine par "OUI" ou "NON" si l'entrée est malveillante.
  
* **Option B : Filtrage et assainissement déterministe local (PromptSanitizer)** Développer un composant applicatif backend en Python pur réalisant une analyse multicouche systématique : normalisation Unicode, détection par expressions régulières (Regex) des motifs d'évasion structurelle, dictionnaire heuristique de mots-clés interdits et échappement automatique des chevrons XML.

* **Option C : Structuration stricte des Prompts et Délimiteurs Système (Défense passive)** Se reposer exclusivement sur l'ingénierie de prompt en encapsulant les entrées de l'utilisateur entre des balises XML strictes au sein du System Prompt et en ordonnant à l'IA d'ignorer les ordres à l'intérieur.

---

## 3. Critères d'Évaluation

| Critères de décision | Option A (LLM Guardrail) | Option B (PromptSanitizer local) | Option C (Prompt pur) |
| :--- | :---: | :---: | :---: |
| **Latence d'exécution** | Mauvaise (+5s à 10s par exécution) | Excellente (< 1ms) | Excellente (0ms induit) |
| **Coût financier & Souveraineté** | Moyen (calcul machine local accru) | Gratuit (calcul CPU standard) | Gratuit |
| **Déterminisme (Fiabilité)** | Probabiliste (risques de faux positifs) | 100 % Déterministe | Faible (les LLM finissent par craquer) |
| **Protection contre l'évasion XML**| Partielle | Absolue (via échappement de chaîne) | Nulle |
| **Complexité d'implémentation** | Élevée (gestion d'un flux asynchrone) | Moyenne (maintien des Regex) | Très faible |

---

## 4. Décision

L'équipe a validé la mise en œuvre de l'**Option B (PromptSanitizer déterministe local)**, combinée avec les principes de l'**Option C (Structuration stricte)**. 

### Justification de la décision :
1. **Sanctuaire de la Latence (Exigence J2)** : L'Option A détruisait complètement les gains de performance obtenus lors de la bascule sur Llama 3.2 3B (ADR-001). L'Option B s'exécute de manière synchrone en mémoire CPU en moins d'une milliseconde.
2. **Robustesse face à la rupture XML** : L'évasion structurelle utilisant des balises fermantes comme `</DATA>` (identifiée comme vecteur d'attaque principal sur les documents téléversés) est mathématiquement résolue par le remplacement des caractères `<` et `>` en entités HTML sûres (`&lt;` et `&gt;`). Le LLM lira les balises comme du texte brut passif sans jamais rompre son conteneur système.
3. **Approche Zero-Trust et Fail-Fast** : En levant une exception logicielle `PromptInjectionException` dès le backend Django, nous coupons la route d'inférence immédiatement. Aucun token malveillant n'est envoyé à Ollama, préservant ainsi la disponibilité de nos ressources d'infrastructure locales.

---

## 5. Conséquences

### Conséquences Positives :
* **Performance maintenue** : Le temps global de réponse pour l'utilisateur final reste inchangé.
* **Sécurité démontrable par tests** : Contrairement aux solutions d'IA probabilistes, nous pouvons garantir le blocage des charges utiles adversariales via une suite de 5 tests d'injections agressives sous `pytest`.
* **Souveraineté préservée** : Tout le code de sécurité s'exécute sur notre serveur local, restant aligné avec notre charte RGPD (100% Local-First).

### Conséquences Négatives / Risques :
* **Maintenance de la liste noire** : Les attaquants font preuve de créativité. Le dictionnaire de mots-clés interdits et les motifs d'expressions régulières devront être mis à jour régulièrement pour couvrir les nouvelles techniques d'évasion (ex: attaques par traduction croisée).
* **Faux positifs potentiels** : Un cours légitime de cybersécurité qui traite précisément des commandes de piratage pourrait être accidentellement bloqué par notre filtre strict. Un mécanisme d'exclusion ou de bypass par l'enseignant admin devra être planifié en Release 2.
